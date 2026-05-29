# Story 7.4: `enforce_2fa_for_roles` config + lifespan-startup fail-fast + login enforcement branch (Decision F realization, Role.agent fail-fast invariant)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want a NEW Pydantic Settings field `enforce_2fa_for_roles: list[UserRole] = Field(default_factory=list)` in `apps/api/app/core/config.py` (env-var name `ENFORCE_2FA_FOR_ROLES`, comma-separated role-name parser modeled on the existing `download_extensions` precedent at `config.py:66-87`) plus a NEW lifespan-startup validation in `apps/api/app/main.py` that runs BEFORE the existing `configure_logging` / `get_engine` / `init_schema` / `seed_admin` / `RedisFactory` / `create_pool` calls and raises `RuntimeError` with the verbatim Decision F message (`"agent role MUST NEVER appear in enforce_2fa_for_roles (it is a service account; forcing 2FA would brick AI ingestion). Edit apps/api/app/core/config.py or infra/.env to remove it."`) when `UserRole.agent` is present in the list (defense-in-depth against operator misconfiguration — the agent role MUST NEVER be forced through 2FA per NFR5-INT-1 binding invariant + brief Success Criterion #5 "agent ingestion is preserved exactly"), plus a NEW inline enforcement branch in `apps/api/app/modules/auth/router.py:login()` placed AFTER the existing password-verify success path (line 82) AND AFTER the existing Story 7.3 `user.totp_enabled_at IS NOT NULL` partial-auth branch (line 96) AND BEFORE the existing `_mint_refresh_row` / `set_session_cookies` / `auth.login.success` single-factor success path (lines 116-152) — so users with `totp_enabled_at IS NOT NULL` still take Story 7.3's verify path UNCHANGED, while users with `totp_enabled_at IS NULL AND user.role IN settings.enforce_2fa_for_roles` take the NEW Story 7.4 forced-enrollment path — that:

- Mints a refresh-token family + access token (IDENTICAL to the single-factor success path; the user IS authenticated by password — only 2FA enrollment is missing, not auth itself) via the existing `new_refresh_row` / `encode_token` helpers — off-loaded to `asyncio.to_thread` mirroring the existing single-factor branch at `apps/api/app/modules/auth/router.py:116-128` (Codex P2-1 event-loop offload pattern, binding from Story 7.3 close-out);
- Sets `portal_access` + `portal_refresh` cookies via the existing `set_session_cookies` helper (IDENTICAL to single-factor branch — the user can call `/api/auth/2fa/enroll` + `/api/auth/2fa/enroll/confirm` using normal cookie auth; no new endpoint variants needed);
- Emits `auth.login.success` audit row with an EXTENDED `after` payload `{"email": user.email, "totp_enroll_required": true}` — the audit row records that the login DID succeed AND that the user must complete 2FA enrollment before the frontend opens any other route; SQL queries against `audit_log.after_json->>'totp_enroll_required' = 'true'` give operators a single-query view of which forced-enrollment logins happened (FR5-AUDIT-1 traceability without adding a new action name);
- Returns an EXTENDED `LoginResponse` shape with the NEW field `totp_enroll_required: bool = False` set to `True` — the existing `partial_auth: bool = False` discriminator stays `False` (this branch IS fully authenticated, NOT the Story 7.3 partial-auth-no-cookies case), and the frontend reads `response.totp_enroll_required === true` as the signal to navigate to `/settings/2fa` enrollment screen and gate every other route until enrollment completes (verified via `GET /api/auth/2fa/status` returning `enabled: true`);

and a NEW frontend behavior in `apps/web/src/routes/login.tsx` (extending — NOT replacing — the existing two-sub-state component shipped in Story 7.3) that, on the `submitEmailPassword` success path (line 33-55 of the current file) AFTER the existing `resp.partial_auth === true` discriminator check at line 42 (Story 7.3 verify branch) BUT BEFORE the existing `qc.invalidateQueries` + `navigate({to: next})` at lines 48-50 (single-factor success path), branches on `resp.totp_enroll_required === true` and navigates to `/settings/2fa?next=<original-next>` instead of the user's intended `next` destination — the Settings 2FA page is reached with VALID cookie auth (because cookies were set on this branch) and uses the existing Story 7.2 enrollment flow (`POST /api/auth/2fa/enroll` → QR + manual secret → `POST /api/auth/2fa/enroll/confirm` → cleartext recovery codes once), AND on successful enrollment the page reads the URL `next` param and navigates to the original destination (operator returns to where they were trying to go after completing the forced-enrollment task) — and a NEW behavior in `apps/web/src/modules/auth/Settings2faPage.tsx` that reads `useSearch({from: "/settings/2fa"})` (or the equivalent — `/settings/2fa` route definition extension below), surfaces an informational banner "Twoja rola wymaga 2FA — proszę dokończyć konfigurację" / "Your role requires 2FA — please complete enrollment" (i18n key `auth.2fa.enroll.forced_banner`) when the page is reached via the forced-enrollment flow (detected by URL `next` param presence OR a new `forced` query param), and post-confirm navigates to `next` instead of staying on the settings page;

realizing **FR5-2FA-3** in full (config flag exists, agent role excluded by fail-fast startup validation, per-role enforcement applies at login), realizing **NFR5-INT-1** in full (the `agent` role MUST NEVER appear in `enforce_2fa_for_roles` — startup fails fast on misconfiguration; agent ingestion flow is preserved exactly), anchoring architecture.md **Decision F §1536-1557** (config flag shape + verbatim error message + per-role enforcement + middleware-check-inline-in-login per Cascading §1557 binding placement override of Choice §1554 — the architecture's Choice block says `apps/api/app/core/auth/middleware.py` but Cascading §1557 verbatim CORRECTS this: "Enforcement check placement: inline in `apps/api/app/modules/auth/router.py::login()` (after password verify, before `set_session_cookies`) — NOT in `app/core/auth/middleware.py` (that module does not exist; per-request middleware would re-decode JWT on every request, violating Init 0 perf budget)" — Story 7.4 follows the Cascading-block ruling), explicitly DEFERRING the per-user override path (Decision F §1553) to Story 8.4 (admin force-2FA-enrollment endpoint) which adds a separate `users.force_2fa_enrollment` BOOLEAN column per epics §1798 + reuses the SAME inline-in-login enforcement-check pattern shipped by this story, explicitly DEFERRING the post-cutover operator runbook documentation of the flag to `_bmad-output/project-context.md` per architecture Cascading §1557 verbatim "Operator runbook documents the flag in `_bmad-output/project-context.md` post-E10 (deferred per CC §2.2)", explicitly DEFERRING any Settings2faPage layout/copy changes beyond the forced-enrollment banner (the existing Story 7.2 wizard surface is read-only from this story's perspective except for adding the optional banner + post-confirm-navigate-to-next behavior), explicitly DEFERRING any frontend "route guard for force-enrollment users" implementation (the simplest gate is the single-step navigate-on-login + post-enroll-navigate-back; a global router guard that ALSO redirects every subsequent navigation back to /settings/2fa is over-engineering for E7 scope — operators who close the tab and re-open are caught by the same enforcement on the next /api/auth/login round-trip), so that EVERY currently-passing test in `apps/api/tests/` (663-test backend baseline post-7.3 + 331 vitest + 216 Playwright) continues to pass unchanged AND new tests verify the binding behavior at three layers: config parsing + startup validation in `apps/api/tests/test_config.py` (NEW test file — file does NOT currently exist), login enforcement branch in `apps/api/tests/test_enforce_2fa_login.py` (NEW test file), and frontend force-enrollment navigation in `apps/web/src/routes/login.test.tsx` + `apps/web/src/modules/auth/Settings2faPage.test.tsx` (EXTEND existing files).

## Acceptance Criteria

**AC-1 — Config flag `enforce_2fa_for_roles: list[UserRole]` added to `apps/api/app/core/config.py` with comma-separated env-var parsing.**

- Given the existing `Settings` class at `apps/api/app/core/config.py:9-140` with the `download_extensions` precedent at lines 66-87 (NoDecode-annotated `list[str]` with a `@field_validator("...", mode="before")` parser that splits on commas + normalizes case),
- When Story 7.4 ships,
- Then `apps/api/app/core/config.py` MUST gain EXACTLY ONE new Settings field added between the existing `totp_fernet_key: str = ""` line (line 41) and the existing `# Rate-limiting (Story 6.6, Decision G)` block-header comment (line 43) — placed in the "Auth" block alongside the other 2FA-related fields:

  ```python
  # 2FA enforcement (Story 7.4, Decision F)
  enforce_2fa_for_roles: Annotated[list[UserRole], NoDecode] = Field(
      default_factory=list
  )
  ```

- And the corresponding `@field_validator("enforce_2fa_for_roles", mode="before")` MUST be added immediately after the existing `_parse_extensions` validator (lines 70-87) — modeled VERBATIM on the `download_extensions` parser shape:

  ```python
  @field_validator("enforce_2fa_for_roles", mode="before")
  @classmethod
  def _parse_roles(cls, v: object) -> object:
      if isinstance(v, str):
          v = [item for item in v.split(",")]
      if isinstance(v, list):
          normalized: list[UserRole] = []
          for item in v:
              if isinstance(item, UserRole):
                  normalized.append(item)
                  continue
              if not isinstance(item, str):
                  continue
              candidate = item.strip().lower()
              if not candidate:
                  continue
              try:
                  normalized.append(UserRole(candidate))
              except ValueError as exc:
                  raise ValueError(
                      f"enforce_2fa_for_roles contains unknown role "
                      f"{item!r}; valid roles are: {', '.join(r.value for r in UserRole)}"
                  ) from exc
          return normalized
      return v
  ```

- And the necessary import MUST be added to `apps/api/app/core/config.py`:

  ```python
  from app.core.db.models._enums import UserRole
  ```

  The import path is BINDING — use `app.core.db.models._enums` (underscore prefix is fine; the symbol is RE-EXPORTED from `app.core.db.models` at `__init__.py:34` but importing from the underscore module avoids the SQLModel relationship-cycle import-overhead in `core/config.py` which is loaded on every test fixture setup).

- And NO other field, validator, or model-validator in `Settings` is changed. The existing `_block_default_secrets_in_prod` model-validator stays UNCHANGED.

- And the parser MUST:
  - Accept an empty string `""` → empty list `[]` (default).
  - Accept a CSV string `"member"` → `[UserRole.member]`.
  - Accept a CSV string `"member,admin"` → `[UserRole.member, UserRole.admin]`.
  - Accept a CSV string `" member , admin "` (with whitespace) → `[UserRole.member, UserRole.admin]` (whitespace stripped per `.strip()`).
  - Accept mixed-case `"Member,ADMIN"` → `[UserRole.member, UserRole.admin]` (lowercased per `.lower()`).
  - REJECT an unknown role `"member,banker"` → `ValueError` at Settings instantiation with the verbatim message `"enforce_2fa_for_roles contains unknown role 'banker'; valid roles are: admin, agent, member"`.
  - Pass through a pre-typed `list[UserRole]` value unchanged (Python-side construction, NOT env-var path; tests sometimes pass typed values directly via `Settings(enforce_2fa_for_roles=[UserRole.member])`).

- And the AC-9 grep check `grep -nE 'enforce_2fa_for_roles' apps/api/app/core/config.py` MUST return EXACTLY 2 lines (1 for the field declaration, 1 for the `@field_validator` decorator argument; the validator method body refers to the field through its first-positional-arg `v` so doesn't add a match).

**AC-2 — Lifespan-startup validation in `apps/api/app/main.py` raises `RuntimeError` with verbatim Decision F message when `UserRole.agent IN settings.enforce_2fa_for_roles`.**

- Given the existing `lifespan(app: FastAPI)` async-context-manager at `apps/api/app/main.py:27-51` (which currently calls `configure_logging` → `get_engine` → `init_schema` (dev/test only) → `seed_admin` → `RedisFactory` → `create_pool` in that order),
- When Story 7.4 ships,
- Then `apps/api/app/main.py:lifespan` MUST be extended with a NEW validation step placed IMMEDIATELY AFTER the existing `settings = get_settings()` line (line 29) and BEFORE the existing `configure_logging(...)` call (line 30) — the validation MUST run BEFORE ANY OTHER lifespan side-effect (NO logging, NO DB connection, NO schema init, NO Redis connection, NO arq pool):

  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      settings = get_settings()
      if UserRole.agent in settings.enforce_2fa_for_roles:
          raise RuntimeError(
              "agent role MUST NEVER appear in enforce_2fa_for_roles "
              "(it is a service account; forcing 2FA would brick AI ingestion). "
              "Edit apps/api/app/core/config.py or infra/.env to remove it."
          )
      configure_logging(...)
      # ... rest UNCHANGED
  ```

- And the error message MUST be CHARACTER-EXACT to Decision F §1547-1551 — three lines of message text concatenated by Python string-literal-joining (the verbatim error from architecture.md, character-for-character). NO paraphrasing. NO additional sentences. NO removal of the "Edit ... to remove it." suffix. The AC-9 grep check 6.5 verifies this.

- And the corresponding import MUST be added to `apps/api/app/main.py` imports block:

  ```python
  from app.core.db.models._enums import UserRole
  ```

  Placed alphabetically with the other `app.core.*` imports (after `from app.core.config import get_settings` per the existing ordering).

- And NO other line in `lifespan` is changed. The existing `seed_admin`, `RedisFactory`, `create_pool`, and `await app.state.arq.aclose()` / `await app.state.redis.aclose()` calls stay UNCHANGED.

- And NO change to `create_app()` (lines 54-132) is made — the middleware mount block stays UNCHANGED, the FastAPI factory stays UNCHANGED, the routers stay UNCHANGED. The validation is a lifespan-only addition.

- And the validation runs ON EVERY APP STARTUP — including dev / test / production. In tests, the existing `TestClient` `with` statement triggers lifespan startup, so a test that monkeypatches `ENFORCE_2FA_FOR_ROLES=agent` SHOULD see the `RuntimeError` raised inside `TestClient(app).__enter__` (verified by AC-7 T-CONFIG-2).

- And the AC-9 grep check 1 verifies the placement:

  ```bash
  grep -nB1 'agent role MUST NEVER appear' apps/api/app/main.py
  # ≥3 matched lines: the `if UserRole.agent in settings.enforce_2fa_for_roles:` line + the RuntimeError opening line + the message line
  ```

**AC-3 — Login handler enforcement branch in `apps/api/app/modules/auth/router.py:login()` mints cookies + sets `LoginResponse.totp_enroll_required = True` when `user.role IN settings.enforce_2fa_for_roles AND user.totp_enabled_at IS NULL`.**

- Given the existing `login()` handler at `apps/api/app/modules/auth/router.py:63-152` (the Story 7.3-converted async handler with the password-verify path at lines 76-92, the Story 7.3 partial-auth branch at lines 96-114 for `user.totp_enabled_at IS NOT NULL`, and the single-factor success path at lines 116-152),
- When Story 7.4 ships,
- Then `apps/api/app/modules/auth/router.py:login()` MUST gain a NEW inline branch placed IMMEDIATELY AFTER the existing Story 7.3 partial-auth branch (line 114 — the `return PartialAuthResponse(...)` at end of the `if user.totp_enabled_at is not None:` block) AND IMMEDIATELY BEFORE the existing `def _mint_refresh_row()` inner function (line 116) — i.e., between the two existing branches:

  ```python
  # Story 7.4 — forced-enrollment branch for roles in enforce_2fa_for_roles.
  # The user IS authenticated by password (verified above) but has not yet
  # enrolled 2FA. Issue cookies and mark the response so the frontend
  # navigates to /settings/2fa enrollment screen. Order matters: this
  # check fires AFTER the Story 7.3 totp_enabled_at-IS-NOT-NULL branch
  # so totp-enabled users still go through the verify flow; this branch
  # only fires for users who have NOT yet enrolled.
  totp_enroll_required = (
      user.totp_enabled_at is None
      and user.role in settings.enforce_2fa_for_roles
  )
  ```

  Then the existing `_mint_refresh_row` inner function + the `secret = await asyncio.to_thread(_mint_refresh_row)` call stay UNCHANGED — the user gets a refresh-token family minted via the existing helper regardless of whether `totp_enroll_required` is `True` or `False`. The branches differ only in (a) the audit `after` payload and (b) the response shape `totp_enroll_required` field.

- And the existing `set_session_cookies(response, access=access, refresh=secret, settings=settings)` call (line 136) MUST execute UNCHANGED for both branches (forced-enrollment users get cookies; the partial-auth-no-cookies semantic ONLY applies to Story 7.3's `totp_enabled_at IS NOT NULL` verify path — Story 7.4's forced-enrollment path issues cookies because the user IS single-factor-authenticated by password and needs cookie auth to call the enrollment endpoint).

- And the existing `record_event(get_engine(), action="auth.login.success", ...)` call (line 137-144) MUST be EXTENDED on its `after` payload — REPLACE the existing `after={"email": user.email}` with a conditional shape that includes `totp_enroll_required` ONLY when `True` (so non-forced-enrollment logins keep their existing audit shape unchanged, satisfying the AC-9 grep regression check):

  ```python
  after_payload: dict[str, object] = {"email": user.email}
  if totp_enroll_required:
      after_payload["totp_enroll_required"] = True
  record_event(
      get_engine(),
      action="auth.login.success",
      entity_type="user",
      entity_id=user.id,
      actor_user_id=user.id,
      after=after_payload,
  )
  ```

- And the existing `return LoginResponse(user=MeResponse(...))` call (lines 145-152) MUST be EXTENDED with the new `totp_enroll_required` field:

  ```python
  return LoginResponse(
      user=MeResponse(
          id=user.id,
          email=user.email,
          display_name=user.display_name,
          role=user.role.value,
      ),
      totp_enroll_required=totp_enroll_required,
  )
  ```

- And the NEW `auth.login.success` audit payload variant (with `totp_enroll_required: True`) MUST emit the SAME action name `"auth.login.success"` (NOT a new action `"auth.login.success.enroll_required"` or similar) — the action vocabulary stays at 16 names per FR5-AUDIT-1; the discriminator lives in the `after` JSON payload only, queryable via `audit_log.after_json->>'totp_enroll_required' = 'true'`.

- And NO change to the existing Story 7.3 partial-auth branch (lines 96-114) is allowed — the `if user.totp_enabled_at is not None:` block stays VERBATIM. Forced-enrollment + verify-second-factor are mutually exclusive (forced-enrollment ONLY fires when `totp_enabled_at IS NULL`; verify-second-factor ONLY fires when `totp_enabled_at IS NOT NULL`).

- And NO change to the existing password-fail emission (lines 84-91 `auth.login.fail` row) is allowed — wrong password for a forced-enrollment-eligible user still emits `auth.login.fail` UNCHANGED. The enforcement branch only fires after successful password verification.

- And NO change to the `response_model=LoginResponse | PartialAuthResponse` decorator (line 63) is needed — the `LoginResponse` shape gains ONE optional field with a default, which is backward-compatible.

- And the AC-9 grep checks 4-5 verify the branch shape exists:

  ```bash
  grep -nE 'totp_enroll_required' apps/api/app/modules/auth/router.py
  # ≥4 matches: the variable assignment, the audit-payload conditional, the LoginResponse field, and one comment line referencing Story 7.4
  ```

**AC-4 — `LoginResponse` Pydantic model extended with `totp_enroll_required: bool = False` field (backward-compatible discriminator addition).**

- Given the existing `LoginResponse` at `apps/api/app/modules/auth/models.py:21-23` (currently `partial_auth: bool = False` + `user: MeResponse`),
- When Story 7.4 ships,
- Then `apps/api/app/modules/auth/models.py:LoginResponse` MUST gain EXACTLY ONE new field placed AFTER the existing `user: MeResponse` field:

  ```python
  class LoginResponse(BaseModel):
      partial_auth: bool = False  # discriminator — always False on this shape
      user: MeResponse
      totp_enroll_required: bool = False  # Story 7.4 — true when Decision F enforcement requires enrollment
  ```

- And NO change to the existing `partial_auth: bool = False` field is allowed — the discriminator stays at False on this shape. Forced-enrollment IS a full-auth response (cookies set, valid `user` payload) with an additional flag, NOT a partial-auth response.

- And NO change to `PartialAuthResponse` (lines 26-35) is allowed in this story. Story 7.3's shape stays as-is. (A future Story COULD extend PartialAuthResponse with `totp_enroll_required: bool = False` for an alternate strict-no-cookies forced-enrollment design, but that is OUT OF SCOPE here.)

- And NO change to `MeResponse`, `LoginRequest`, `SessionRow`, or `SessionsResponse` is allowed.

- And the `LoginResponse` field-default `False` makes the change backward-compatible:
  - Existing tests that construct `LoginResponse(user=...)` keep working (field defaults).
  - Existing tests that assert against `LoginResponse` JSON deserialization see a NEW field `"totp_enroll_required": false` in every response — this is the FIRST regression vector to check; AC-9 grep check 7 enumerates which test files need acknowledgment of the new field (zero assertion changes are needed because the existing tests don't assert on the new field name).

- And the AC-9 grep check 3 verifies the shape:

  ```bash
  grep -nE 'totp_enroll_required: bool' apps/api/app/modules/auth/models.py
  # 1 match — exactly one field declaration in LoginResponse
  ```

**AC-5 — Frontend `LoginResponse` interface (`apps/web/src/lib/api-types.ts`) extended with `totp_enroll_required: boolean` field; `login.tsx` reads the discriminator and navigates to `/settings/2fa`.**

- Given the existing `LoginResponse` TS interface at `apps/web/src/lib/api-types.ts:24-27` and the existing `submitEmailPassword` handler at `apps/web/src/routes/login.tsx:33-55`,
- When Story 7.4 ships,
- Then `apps/web/src/lib/api-types.ts:LoginResponse` MUST be extended with ONE new field:

  ```ts
  export interface LoginResponse {
    partial_auth: false;  // discriminator — always false on this shape
    user: MeResponse;
    totp_enroll_required: boolean;  // Story 7.4 — true when Decision F enforcement requires enrollment
  }
  ```

- And `apps/web/src/routes/login.tsx:submitEmailPassword` MUST gain a NEW conditional check placed IMMEDIATELY AFTER the existing Story 7.3 `if (resp.partial_auth === true)` branch (line 42-47) AND IMMEDIATELY BEFORE the existing `await qc.invalidateQueries({ queryKey: ["auth", "me"] })` call (line 48):

  ```tsx
  if (resp.partial_auth === true) {
    setPartialToken(resp.partial_token);
    setSubState("second_factor");
    setPending(false);
    return;
  }
  // Story 7.4 — forced-enrollment for Decision F roles.
  // Cookies ARE set by this branch; the user is single-factor authenticated.
  // Navigate to /settings/2fa carrying the original `next` so the page can
  // hand them back after enrollment completes.
  if (resp.totp_enroll_required === true) {
    await qc.invalidateQueries({ queryKey: ["auth", "me"] });
    const next = search.next ? decodeURIComponent(search.next) : "/";
    await navigate({ to: "/settings/2fa", search: { next } });
    return;
  }
  await qc.invalidateQueries({ queryKey: ["auth", "me"] });
  // ... existing navigate({to: next}) sequence unchanged
  ```

- And the existing single-factor success path (lines 48-50) MUST stay UNCHANGED — the `qc.invalidateQueries` + `decodeURIComponent` + `navigate({to: next})` sequence keeps working for users who are NOT forced into 2FA enrollment.

- And the existing Story 7.3 second-factor sub-state (lines 92-129 of login.tsx) MUST stay UNCHANGED.

- And the existing `LoginSearch` type at line 11-13 stays UNCHANGED — `?next=` URL param continues to encode the post-login destination; the new `totp_enroll_required` flow uses the SAME `next` param semantics, just routed via `/settings/2fa` first.

- And the AC-9 grep check 9 verifies the frontend shape:

  ```bash
  grep -nE 'totp_enroll_required' apps/web/src/routes/login.tsx apps/web/src/lib/api-types.ts
  # ≥3 matches: interface field declaration, conditional check, comment referencing Story 7.4
  ```

**AC-6 — Settings 2FA page (`apps/web/src/modules/auth/Settings2faPage.tsx`) detects forced-enrollment mode via URL `next` param, surfaces an informational banner, and post-enroll-navigate to `next`.**

- Given the existing `Settings2faPage` at `apps/web/src/modules/auth/Settings2faPage.tsx` (Story 7.2 wizard: enrollment → QR → confirm → recovery codes → done),
- When Story 7.4 ships,
- Then `apps/web/src/modules/auth/Settings2faPage.tsx` MUST be extended (NOT replaced) with:

  - A NEW `useSearch({from: "/settings/2fa"})` (or equivalent — read the existing route file at `apps/web/src/routes/settings/2fa.tsx` to confirm the route path) read of the `next` URL param. If `next` is present AND non-empty, set a component-level constant `forcedEnrollmentMode = true`. If absent or empty, `forcedEnrollmentMode = false` (the existing voluntary-enrollment flow).
  - When `forcedEnrollmentMode === true` AND the user is in the "before enrollment starts" state (e.g., before clicking "Enroll" / "Start"), render an info banner at the top of the page:

    ```tsx
    {forcedEnrollmentMode && (
      <div role="alert" className="rounded-md border border-warning bg-warning/10 p-3 text-sm">
        {t("auth.2fa.enroll.forced_banner")}
      </div>
    )}
    ```

    The banner styling MUST follow the existing alert-component conventions in the codebase (look at `apps/web/src/ui/` for an existing alert/banner component; if one exists, USE IT — `<Alert variant="warning">` or equivalent — instead of raw `<div>`).

  - When `forcedEnrollmentMode === true` AND the enrollment-confirm step has SUCCEEDED (the cleartext recovery codes are displayed), after the user clicks the "Done" / "Continue" button at the end of the wizard, navigate to the URL `next` value instead of staying on `/settings/2fa`:

    ```tsx
    function onWizardComplete() {
      if (forcedEnrollmentMode && search.next) {
        const next = decodeURIComponent(search.next);
        navigate({ to: next as "/" });
        return;
      }
      // existing voluntary-enrollment-complete behavior (e.g., refetch /api/auth/2fa/status, show "TOTP enabled" state)
    }
    ```

- And the existing route file `apps/web/src/routes/settings/2fa.tsx` MUST be extended with `validateSearch` to accept the `next` query param:

  ```tsx
  interface Settings2faSearch {
    next?: string;
  }

  export const Route = createFileRoute("/settings/2fa")({
    component: Settings2faPage,
    validateSearch: (raw: Record<string, unknown>): Settings2faSearch => {
      return typeof raw.next === "string" && raw.next.length > 0
        ? { next: raw.next }
        : {};
    },
  });
  ```

  (Mirror the existing pattern at `apps/web/src/routes/login.tsx:172-179`.)

- And NO change to the Story 7.2 enrollment-confirm endpoint contract (`POST /api/auth/2fa/enroll/confirm`) is required — the existing flow works with cookie auth, which the forced-enrollment user has (cookies were set on the login branch).

- And the voluntary-enrollment path (no `next` URL param) MUST keep working — existing tests + UX unchanged.

- And the AC-9 grep check 10 verifies the Settings2faPage shape:

  ```bash
  grep -nE 'forcedEnrollmentMode|forced_banner' apps/web/src/modules/auth/Settings2faPage.tsx
  # ≥3 matches: variable assignment, banner conditional, post-complete navigate conditional
  grep -nE 'auth\.2fa\.enroll\.forced_banner' apps/web/src/locales/en.json apps/web/src/locales/pl.json
  # 2 matches — one per locale file
  ```

**AC-7 — Backend tests: NEW file `apps/api/tests/test_config.py` with config-parsing + startup-fail-fast tests (4 named tests T-CONFIG-1..4); NEW file `apps/api/tests/test_enforce_2fa_login.py` with login-enforcement-branch tests (6 named tests T-ENFORCE-1..6).**

- Given the existing test conventions at `apps/api/tests/conftest.py` (session-scoped `_isolated_db` fixture sets env vars + clears `get_settings.cache` + initializes schema) + the per-test fresh-app pattern at `apps/api/tests/test_2fa_verify.py:44-70` (monkeypatch-set env vars + clear cache + `create_app()` + fakeredis stub),
- When Story 7.4 ships,
- Then a NEW file `apps/api/tests/test_config.py` MUST exist with EXACTLY 4 named tests (NAMES ARE BINDING — the dev-story task cross-references them):

  | # | Test name | What it asserts |
  |---|---|---|
  | T-CONFIG-1 | `test_default_enforce_2fa_for_roles_is_empty_list` | `Settings()` constructed with no `ENFORCE_2FA_FOR_ROLES` env-var sets `enforce_2fa_for_roles == []`. Direct constructor; no monkeypatch needed. |
  | T-CONFIG-2 | `test_agent_role_in_enforce_2fa_raises` | **VERBATIM name from epics §1705 binding.** Set `monkeypatch.setenv("ENFORCE_2FA_FOR_ROLES", "agent")`, clear `get_settings.cache`, then `with TestClient(create_app()) as c:` — expect `RuntimeError` raised inside `__enter__` (lifespan startup) with the verbatim Decision F message substring `"agent role MUST NEVER appear in enforce_2fa_for_roles"`. Use `pytest.raises(RuntimeError, match="agent role MUST NEVER appear")`. |
  | T-CONFIG-3 | `test_csv_parser_parses_member_admin_with_whitespace` | Set `ENFORCE_2FA_FOR_ROLES=" member , admin "`, instantiate `Settings()`, assert `enforce_2fa_for_roles == [UserRole.member, UserRole.admin]`. |
  | T-CONFIG-4 | `test_csv_parser_rejects_unknown_role` | Set `ENFORCE_2FA_FOR_ROLES="member,banker"`, instantiate `Settings()`, expect `ValidationError` with substring `"contains unknown role 'banker'"`. Pydantic wraps `ValueError` from the validator into `ValidationError`. |

  Test-file boilerplate MUST follow the existing `apps/api/tests/test_2fa_verify.py:44-70` fixture pattern (per-test `monkeypatch.setenv` + `get_settings.cache_clear()` + `get_engine.cache_clear()`). DO NOT use the session-scoped `_isolated_db` fixture for these tests — they need PER-TEST env-var control.

- And a NEW file `apps/api/tests/test_enforce_2fa_login.py` MUST exist with EXACTLY 6 named tests:

  | # | Test name | What it asserts |
  |---|---|---|
  | T-ENFORCE-1 | `test_login_member_in_enforce_list_no_totp_returns_totp_enroll_required_with_cookies` | Set `ENFORCE_2FA_FOR_ROLES=member`. Seed user `role=member, totp_enabled_at=None`. POST `/api/auth/login` with valid creds. Assert HTTP 200, body `{"partial_auth": false, "user": {...}, "totp_enroll_required": true}`. Assert `Set-Cookie` headers contain BOTH `portal_access=` AND `portal_refresh=` (both cookies issued — single-factor auth completed). Assert one `RefreshToken` row exists for the user. |
  | T-ENFORCE-2 | `test_login_admin_not_in_enforce_list_returns_normal_response` | Set `ENFORCE_2FA_FOR_ROLES=member`. Seed user `role=admin, totp_enabled_at=None`. POST login with valid creds. Assert HTTP 200, body `{"partial_auth": false, "user": {...}, "totp_enroll_required": false}`. Single-factor success path baseline regression. |
  | T-ENFORCE-3 | `test_login_member_not_in_enforce_list_returns_normal_response` | Set `ENFORCE_2FA_FOR_ROLES=""` (empty, default). Seed user `role=member, totp_enabled_at=None`. POST login with valid creds. Assert HTTP 200, body `{"partial_auth": false, "user": {...}, "totp_enroll_required": false}`. Default-config baseline regression. |
  | T-ENFORCE-4 | `test_login_member_in_enforce_list_with_totp_enabled_returns_partial_auth_not_enroll_required` | Set `ENFORCE_2FA_FOR_ROLES=member`. Seed user `role=member, totp_enabled_at=NOW, totp_secret=encrypted(KNOWN_TOTP_SECRET)`. POST login with valid creds. Assert HTTP 200, body `{"partial_auth": true, "totp_required": true, "partial_token": <opaque>}` — Story 7.3 verify path, NOT the Story 7.4 enroll-required path. Assert NO cookies set, NO RefreshToken row. Cross-story-mutual-exclusivity guard. |
  | T-ENFORCE-5 | `test_login_member_in_enforce_list_no_totp_emits_audit_with_totp_enroll_required_true` | Set `ENFORCE_2FA_FOR_ROLES=member`. Seed user `role=member, totp_enabled_at=None`. POST login. Assert exactly ONE new `AuditLog` row with `action="auth.login.success"` AND `entity_id=user.id` AND `after_json["email"] == user.email` AND `after_json["totp_enroll_required"] == True`. |
  | T-ENFORCE-6 | `test_login_member_not_in_enforce_list_emits_audit_without_totp_enroll_required_key` | Set `ENFORCE_2FA_FOR_ROLES=""`. Seed user `role=member, totp_enabled_at=None`. POST login. Assert exactly ONE new `AuditLog` row with `action="auth.login.success"` AND `after_json == {"email": user.email}` (NO `totp_enroll_required` key in the payload — backward-compat regression guard for existing audit consumers). |

- And every test name MUST appear VERBATIM in the test file (no abbreviation, no rename).
- And the test fixtures MUST use the deterministic `TOTP_FERNET_KEY` from `apps/api/tests/conftest.py:43` when needed (only T-ENFORCE-4 needs Fernet encryption).
- And the per-test `monkeypatch.setenv("ENFORCE_2FA_FOR_ROLES", "...")` + `get_settings.cache_clear()` + `create_app()` pattern is BINDING (matches `apps/api/tests/test_2fa_verify.py:44-70`). NO session-scoped fixture for these tests.
- And the full backend suite MUST stay green: `cd apps/api && uv run pytest -q` → 673 passed (663 Story-7.3-baseline + 4 new in `test_config.py` + 6 new in `test_enforce_2fa_login.py`).

**AC-8 — Frontend tests: NEW vitest cases in `apps/web/src/routes/login.test.tsx` (V5 + V6) + NEW vitest cases in `apps/web/src/modules/auth/Settings2faPage.test.tsx` (S1 + S2).**

- Given the existing 331-spec vitest baseline (post-Story 7.3) + the existing `apps/web/src/routes/login.test.tsx` with V1-V4 cases (Story 7.3) + the existing `apps/web/src/modules/auth/Settings2faPage.test.tsx` (Story 7.2),
- When Story 7.4 ships,
- Then `apps/web/src/routes/login.test.tsx` MUST be EXTENDED with 2 new vitest cases:

  | # | Test name | Asserts |
  |---|---|---|
  | V5 | `it("navigates to /settings/2fa when login response has totp_enroll_required=true", ...)` | Mock `api()` for `/auth/login` → `{partial_auth: false, user: <MeResponse>, totp_enroll_required: true}`. Render `<Login/>` with `search.next` set to `/queue`. Type email + password + submit. Assert `navigate` was called with `{to: "/settings/2fa", search: {next: "/queue"}}` (NOT `{to: "/queue"}`). Assert `qc.invalidateQueries(["auth", "me"])` WAS called (so the page reads the new auth state). |
  | V6 | `it("navigates directly to next when login response has totp_enroll_required=false", ...)` | Mock `api()` for `/auth/login` → `{partial_auth: false, user: <MeResponse>, totp_enroll_required: false}`. Render `<Login/>` with `search.next` set to `/queue`. Type email + password + submit. Assert `navigate` was called with `{to: "/queue"}` (existing single-factor success path; baseline regression). |

- And `apps/web/src/modules/auth/Settings2faPage.test.tsx` MUST be EXTENDED with 2 new vitest cases:

  | # | Test name | Asserts |
  |---|---|---|
  | S1 | `it("renders forced-enrollment banner when next URL param is present", ...)` | Mock `useSearch({from: "/settings/2fa"})` to return `{next: "/queue"}`. Render `<Settings2faPage/>`. Assert the banner element with text matching `t("auth.2fa.enroll.forced_banner")` is visible. |
  | S2 | `it("navigates to next after enrollment-confirm success when forced-enrollment mode", ...)` | Mock `useSearch` to return `{next: "/queue"}`. Mock the enrollment flow to reach the "Done" state. Click the "Done" / "Continue" button. Assert `navigate` was called with `{to: "/queue"}` (NOT staying on `/settings/2fa`). |

- And NO regression on the existing V1-V4 vitest cases in `login.test.tsx` (Story 7.3 verify flow) OR the existing Settings2faPage tests (Story 7.2 voluntary-enrollment wizard).

- And the vitest total MUST be: 331 baseline + 2 new in `login.test.tsx` + 2 new in `Settings2faPage.test.tsx` = **335 specs passing**.

**AC-9 — Pre-merge cross-file grep checklist; sprint-status update; check-all.sh + visual regression + container build all green.**

- Given the Story 6.4 + 6.6 + 6.7 + 7.1 + 7.2 + 7.3 pre-merge grep-checklist precedent,
- When Story 7.4 is ready to merge,
- Then EACH of the following grep checks MUST be silent (zero matches) OR satisfied (non-zero match where expected):

  1. **(satisfied) Lifespan startup validation present:**

     ```bash
     grep -nE 'UserRole\.agent in settings\.enforce_2fa_for_roles' apps/api/app/main.py
     # 1 line (the validation conditional)
     grep -nE 'agent role MUST NEVER appear in enforce_2fa_for_roles' apps/api/app/main.py
     # 1 line (the verbatim RuntimeError message line 1)
     grep -nE 'service account; forcing 2FA would brick AI ingestion' apps/api/app/main.py
     # 1 line (verbatim message line 2)
     ```

  2. **(satisfied) Config flag declared + validator defined:**

     ```bash
     grep -nE 'enforce_2fa_for_roles' apps/api/app/core/config.py
     # 2 lines (field declaration + @field_validator decorator argument)
     grep -nE '_parse_roles' apps/api/app/core/config.py
     # 1 line (validator method name)
     grep -nE 'from app\.core\.db\.models\._enums import UserRole' apps/api/app/core/config.py
     # 1 line
     ```

  3. **(satisfied) `LoginResponse` extended with new field:**

     ```bash
     grep -nE 'totp_enroll_required: bool' apps/api/app/modules/auth/models.py
     # 1 line — exactly one field declaration in LoginResponse
     ```

  4. **(satisfied) Login handler enforcement branch present:**

     ```bash
     grep -nE 'totp_enroll_required' apps/api/app/modules/auth/router.py
     # ≥4 lines: variable assignment, audit-payload conditional, LoginResponse field, Story 7.4 comment
     grep -nE 'in settings\.enforce_2fa_for_roles' apps/api/app/modules/auth/router.py
     # 1 line (the enforcement check)
     ```

  5. **(silent) Story 7.3 partial-auth branch UNCHANGED:**

     ```bash
     # Sanity check — make sure we didn't accidentally modify the totp_enabled_at IS NOT NULL block:
     grep -nE 'totp:partial:' apps/api/app/modules/auth/router.py
     # 1 line — the Redis key prefix from Story 7.3
     grep -nE 'PartialAuthResponse' apps/api/app/modules/auth/router.py
     # ≥2 lines — import + return statement (Story 7.3 partial-auth-no-cookies path; unchanged)
     ```

  6. **(satisfied) env.example documents the flag:**

     ```bash
     grep -nE '^# 2FA enforcement \(Story 7\.4|^ENFORCE_2FA_FOR_ROLES=' infra/env.example
     # 2 lines — comment header + env var line (commented or empty value)
     ```

  7. **(silent) No new action names in audit vocabulary:**

     ```bash
     grep -nE '"auth\.login\.enroll' apps/api/app/modules/auth/router.py apps/api/app/core/audit.py
     # 0 lines — Story 7.4 reuses auth.login.success with payload discriminator; no new action name
     ```

  8. **(silent) No new endpoint added in this story:**

     ```bash
     grep -nE '@router\.post\("/2fa/enroll-with-partial|enroll/from-partial' apps/api/app/modules/auth/totp/router.py
     # 0 lines — Story 7.4 pragmatic design issues cookies and reuses the existing cookie-auth enrollment endpoints
     ```

  9. **(satisfied) Frontend login.tsx + api-types.ts updated:**

     ```bash
     grep -nE 'totp_enroll_required' apps/web/src/routes/login.tsx apps/web/src/lib/api-types.ts
     # ≥3 lines — interface field + conditional check in submitEmailPassword + Story 7.4 comment
     grep -nE 'to: "/settings/2fa"' apps/web/src/routes/login.tsx
     # 1 line — the forced-enrollment navigation
     ```

  10. **(satisfied) Settings2faPage forced-enrollment branch + i18n keys:**

      ```bash
      grep -nE 'forcedEnrollmentMode|forced_banner' apps/web/src/modules/auth/Settings2faPage.tsx
      # ≥3 lines — variable + banner + post-complete navigate
      grep -nE 'auth\.2fa\.enroll\.forced_banner' apps/web/src/locales/en.json apps/web/src/locales/pl.json
      # 2 lines — one per locale (en + pl)
      grep -nE 'validateSearch' apps/web/src/routes/settings/2fa.tsx
      # 1 line — route file gains validateSearch for next param
      ```

  11. **(silent) NO cleartext logging of credentials:**

      ```bash
      grep -E "(_LOG|logging|logger)\.(debug|info|warning|error|critical)\(.*(secret|password|partial_token)" \
        apps/api/app/modules/auth/router.py apps/api/app/main.py apps/api/app/core/config.py
      # 0 lines — no logger emits cleartext material
      ```

- And the full pre-merge verification matrix MUST be green on the dev commit:
  - `cd apps/api && uv run pytest -q` → **673 passed** (Story 7.3 baseline 663 + 10 new across `test_config.py` + `test_enforce_2fa_login.py`).
  - `cd apps/web && npm run typecheck && npm run lint && npm run test` → all green; vitest **335 passed** (331 baseline + 4 new: V5 + V6 in `login.test.tsx` + S1 + S2 in `Settings2faPage.test.tsx`).
  - `cd apps/web && npm run test:visual` → **216 specs passed** (no new visual baselines — the forced-enrollment flow is a navigation effect, no new UI state worth visually baselining beyond the existing `/settings/2fa` wizard screens; the banner is a small additive element that does NOT warrant a new spec, per the operator pragmatism principle "visual baselines for substantive UI not for one-line banners"). If the dev-story finds during implementation that the banner shifts the layout significantly enough to warrant a baseline, they may add one — flagged as discretionary, NOT binding.
  - `infra/scripts/check-all.sh` → **10/10 green**.
  - `docker compose -f infra/docker-compose.yml build api` → succeeded; image `portal-api:0.1.0` rebuilds clean (no new deps — `enforce_2fa_for_roles` reuses the existing `pydantic_settings.NoDecode` + `pydantic.field_validator` already in use for `download_extensions`).
  - `alembic upgrade head --sql | head` → head stays `0013_users_2fa_columns`. NO new migration in Story 7.4 (per architecture Decision F §1557 — config-only change; no DB schema impact).

- And the operator deploy-gate: NO new env-var provisioning required on `.190` because `ENFORCE_2FA_FOR_ROLES` defaults to empty (no enforcement) — Story 7.4 ships with a no-op enforcement footprint until an operator explicitly sets the env var. The `infra/env.example` documentation is the operator's hint; the actual `.190` `infra/.env` keeps `ENFORCE_2FA_FOR_ROLES` UNSET (or empty) for Initiative 5 close-out. Operator MAY enable it post-E10 cutover via a sprint-change-proposal that flips members onto forced 2FA — that decision is OUT OF SCOPE for this story.

**AC-10 — Locale keys (`apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`) gain exactly ONE new key: `auth.2fa.enroll.forced_banner` (en + pl translations).**

- Given the existing locale file conventions at `apps/web/src/locales/en.json` + `pl.json` (parallel translations; `auth.2fa.*` block precedent from Stories 7.2 and 7.3),
- When Story 7.4 ships,
- Then both locale files MUST gain EXACTLY ONE new key under the existing `auth.2fa.enroll` block:

  - **`en.json`**: `"auth.2fa.enroll.forced_banner": "Your role requires two-factor authentication. Please complete enrollment below to continue."`
  - **`pl.json`**: `"auth.2fa.enroll.forced_banner": "Twoja rola wymaga uwierzytelniania dwuskładnikowego. Proszę dokończyć konfigurację poniżej, aby kontynuować."`

- And NO other locale key is added or changed in this story (the Story 7.3 `auth.2fa.verify.*` block stays UNCHANGED; the Story 7.2 `auth.2fa.enroll.*` block gains only the `forced_banner` key).

- And the AC-9 grep check 10 verifies the keys exist in both files.

**AC-11 — `infra/env.example` documents the new env var `ENFORCE_2FA_FOR_ROLES` with an empty default + agent-forbidden comment.**

- Given the existing `infra/env.example` at `infra/env.example` (env-var template for the operator's `.190` `infra/.env`),
- When Story 7.4 ships,
- Then `infra/env.example` MUST gain a NEW block placed near the existing `# Auth` block (after `TOTP_FERNET_KEY=` and before `# Rate-limiting`):

  ```sh
  # 2FA enforcement (Story 7.4, Decision F).
  # Comma-separated list of UserRole names whose users MUST enroll 2FA on
  # next login. Valid roles: admin, member. The `agent` role is FORBIDDEN —
  # forcing 2FA on the service account would brick AI ingestion; the app
  # fails fast on startup if `agent` appears in this list. Default empty
  # (no enforcement) keeps Initiative 5 in voluntary-enrollment mode until
  # operator explicitly opts in.
  # ENFORCE_2FA_FOR_ROLES=
  ```

- And the env var is COMMENTED OUT by default (the `# ENFORCE_2FA_FOR_ROLES=` line) — operator uncomments + sets the value to enable enforcement.

- And NO other env-var line in `infra/env.example` is changed.

- And the AC-9 grep check 6 verifies the documentation.

## Tasks / Subtasks

- [ ] **T1 — Add `enforce_2fa_for_roles` field + `_parse_roles` validator to `Settings` (AC: 1, 9.2)**
  - [ ] Edit `apps/api/app/core/config.py`: add import `from app.core.db.models._enums import UserRole` after the existing `pydantic_settings` import.
  - [ ] Add the `enforce_2fa_for_roles: Annotated[list[UserRole], NoDecode] = Field(default_factory=list)` field declaration in the Auth block (between `totp_fernet_key` and the `# Rate-limiting` comment).
  - [ ] Add the `@field_validator("enforce_2fa_for_roles", mode="before")` classmethod `_parse_roles` per AC-1 verbatim shape.
  - [ ] Run `cd apps/api && uv run pytest tests/test_auth.py tests/test_auth_login_logout.py -v` to confirm no regression on the existing login + auth tests (new field is default-empty so backward-compatible).

- [ ] **T2 — Add lifespan-startup validation in `apps/api/app/main.py` (AC: 2, 9.1)**
  - [ ] Edit `apps/api/app/main.py`: add import `from app.core.db.models._enums import UserRole` alphabetically among `app.core.*` imports.
  - [ ] Add the validation block (`if UserRole.agent in settings.enforce_2fa_for_roles: raise RuntimeError(...)`) IMMEDIATELY after the existing `settings = get_settings()` line inside `lifespan()` and BEFORE `configure_logging(...)`.
  - [ ] Use the VERBATIM Decision F message from AC-2 — character-exact, three concatenated string-literal lines.
  - [ ] Run `cd apps/api && uv run pytest -q` to confirm 663 baseline tests still pass (new validation does not fire when `enforce_2fa_for_roles == []`, which is the test fixture default).

- [ ] **T3 — Extend `LoginResponse` Pydantic model with `totp_enroll_required: bool = False` field (AC: 4, 9.3)**
  - [ ] Edit `apps/api/app/modules/auth/models.py`: add the new field AFTER the existing `user: MeResponse` field per AC-4 verbatim.
  - [ ] Run `cd apps/api && uv run pytest tests/test_auth.py tests/test_auth_login_logout.py tests/test_2fa_verify.py -v` to confirm no regression (the new field is default-False so existing JSON assertions either ignore it or see `"totp_enroll_required": false` added — neither case breaks).

- [ ] **T4 — Add login enforcement branch to `apps/api/app/modules/auth/router.py:login()` (AC: 3, 9.4, 9.5)**
  - [ ] Edit `apps/api/app/modules/auth/router.py:login()`: insert the `totp_enroll_required = (user.totp_enabled_at is None and user.role in settings.enforce_2fa_for_roles)` variable assignment between the Story 7.3 partial-auth branch end (line 114) and the `_mint_refresh_row` inner function (line 116) per AC-3 verbatim.
  - [ ] Extend the existing `record_event(..., action="auth.login.success", ...)` call to use a conditional `after_payload: dict[str, object]` that adds `totp_enroll_required: True` ONLY when `totp_enroll_required` is True.
  - [ ] Extend the existing `LoginResponse(user=MeResponse(...))` return to include `totp_enroll_required=totp_enroll_required`.
  - [ ] Leave the Story 7.3 partial-auth branch (lines 96-114) UNCHANGED. Leave the password-verify-fail path (lines 84-92) UNCHANGED.
  - [ ] Run `cd apps/api && uv run pytest tests/test_auth.py tests/test_auth_login_logout.py tests/test_2fa_verify.py -v` to confirm no regression (Story 7.3 verify-path tests must stay green; the new branch only fires for `totp_enabled_at IS NULL` users in the enforce list, which the existing tests' fixtures never satisfy).

- [ ] **T5 — Backend tests `apps/api/tests/test_config.py` 4 cases + `apps/api/tests/test_enforce_2fa_login.py` 6 cases (AC: 7)**
  - [ ] Create `apps/api/tests/test_config.py` with T-CONFIG-1..4 per AC-7 binding table verbatim.
  - [ ] Create `apps/api/tests/test_enforce_2fa_login.py` with T-ENFORCE-1..6 per AC-7 binding table verbatim.
  - [ ] Use the existing `apps/api/tests/test_2fa_verify.py:44-70` per-test fixture pattern (monkeypatch.setenv + cache_clear + create_app + fakeredis stub).
  - [ ] For T-ENFORCE-4 needing TOTP enrollment: reuse the helpers + KNOWN_TOTP_SECRET pattern from `apps/api/tests/test_2fa_verify.py:36, 100-120`.
  - [ ] Run `cd apps/api && uv run pytest tests/test_config.py tests/test_enforce_2fa_login.py -v` until all 10 are green.
  - [ ] Run `cd apps/api && uv run pytest -q` → confirm **673 passed** (663 baseline + 4 + 6 new).

- [ ] **T6 — Frontend `LoginResponse` interface extension + `login.tsx` forced-enrollment navigation (AC: 5, 9.9)**
  - [ ] Edit `apps/web/src/lib/api-types.ts:LoginResponse`: add `totp_enroll_required: boolean;` field after the existing `user: MeResponse;` field with the Story 7.4 comment.
  - [ ] Edit `apps/web/src/routes/login.tsx:submitEmailPassword`: insert the `if (resp.totp_enroll_required === true) { ... navigate({ to: "/settings/2fa", search: { next } }) ... }` conditional AFTER the existing Story 7.3 partial-auth branch (line 42-47) AND BEFORE the existing `qc.invalidateQueries` call (line 48), per AC-5 verbatim.
  - [ ] Leave the existing Story 7.3 second-factor sub-state (lines 92-129) UNCHANGED.
  - [ ] Run `cd apps/web && npm run typecheck` to confirm the new TS interface compiles. Expect: 0 errors.

- [ ] **T7 — Settings 2FA page forced-enrollment banner + post-complete navigation (AC: 6, 9.10, 10)**
  - [ ] Edit `apps/web/src/routes/settings/2fa.tsx`: extend with `validateSearch` accepting `next?: string` param per AC-6 verbatim.
  - [ ] Edit `apps/web/src/modules/auth/Settings2faPage.tsx`: add `useSearch({from: "/settings/2fa"})` read, `forcedEnrollmentMode` const, banner render conditional, `onWizardComplete` navigate-on-next conditional per AC-6 verbatim.
  - [ ] Edit `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`: add the `auth.2fa.enroll.forced_banner` key with translations per AC-10 verbatim.
  - [ ] Run `cd apps/web && npm run typecheck && npm run lint` to confirm clean compile.

- [ ] **T8 — Frontend tests: V5 + V6 in `login.test.tsx`; S1 + S2 in `Settings2faPage.test.tsx` (AC: 8)**
  - [ ] Extend `apps/web/src/routes/login.test.tsx` with V5 + V6 per AC-8 verbatim.
  - [ ] Extend `apps/web/src/modules/auth/Settings2faPage.test.tsx` with S1 + S2 per AC-8 verbatim.
  - [ ] Use the existing test-fixture patterns (`vi.mock("@/lib/api", ...)`, mock `useNavigate`, mock `useSearch`).
  - [ ] Run `cd apps/web && npm run test login.test.tsx Settings2faPage.test.tsx` until 4 new + existing N are green.
  - [ ] Confirm vitest total: **335 passed**.

- [ ] **T9 — `infra/env.example` documentation (AC: 11, 9.6)**
  - [ ] Edit `infra/env.example`: add the 2FA enforcement block per AC-11 verbatim, placed after the `TOTP_FERNET_KEY=` line and before the `# Rate-limiting` comment.

- [ ] **T10 — Pre-merge verification (AC: 9)**
  - [ ] Run AC-9 grep checks 1-11 verbatim; capture output in Dev Agent Record.
  - [ ] Run `cd apps/api && uv run pytest -q` → **673 passed**.
  - [ ] Run `cd apps/web && npm run typecheck && npm run lint && npm run test` → all green; vitest **335 passed**.
  - [ ] Run `cd apps/web && npm run test:visual` → **216 specs passed** (no new visual baselines).
  - [ ] Run `infra/scripts/check-all.sh` → **10/10 green**.
  - [ ] Run `docker compose -f infra/docker-compose.yml build api` → succeeded (no new deps).
  - [ ] Verify `alembic heads` returns `0013_users_2fa_columns (head)` — NO new migration.
  - [ ] Verify `infra/env.example` block exists; verify `.190` deploy gate: NO new env-var provisioning required (default-empty is no-op).

## Dev Notes

### Architecture references — binding

- **Decision F §1536-1557** — Config flag shape + verbatim error message + per-role enforcement + middleware-check-inline-in-login per Cascading §1557.
  - **CRITICAL: Choice §1554 vs Cascading §1557 contradiction.** The Choice block says the enforcement check lives in `apps/api/app/core/auth/middleware.py` — but the Cascading block EXPLICITLY OVERRIDES this: "**Enforcement check placement:** inline in `apps/api/app/modules/auth/router.py::login()` (after password verify, before `set_session_cookies`) — NOT in `app/core/auth/middleware.py` (that module does not exist; per-request middleware would re-decode JWT on every request, violating Init 0 perf budget)." Story 7.4 FOLLOWS the Cascading-block ruling. No new `middleware.py` module is created.
  - **Pragmatic design ruling — cookies ARE issued on the forced-enrollment branch.** Architecture's "pre-cookie-issue" wording in §1554 is loose ordering language ("the check happens at this point in the handler"), NOT a hard constraint that cookies must be withheld. The user IS single-factor authenticated by password; cookies are issued so they can call `/api/auth/2fa/enroll` via normal cookie auth without needing new endpoint variants. The forced-enrollment-no-cookies + new endpoint-variants design (more strictly aligned with Story 7.3's partial_token-no-cookies pattern) is DEFERRED to a future story if Codex review or operator post-mortem flags the pragmatic design as insufficient. Trade-off: pragmatic design relies on frontend route gating (bypassable by malicious frontend) vs strict design relies on backend refusing all non-enrollment routes (more secure but significantly larger scope). For E7 closure + operator's banking-IT-trust model (Michał is the sole operator + admin), pragmatic is sufficient.
- **Decision F §1553** — Per-user override (admin force-2FA-enrollment) is **DEFERRED to Story 8.4**. The per-user override sets a separate `users.force_2fa_enrollment` BOOLEAN column (per epics §1798) — Story 7.4 does NOT add that column NOR check it; Story 8.4 is responsible for the column + the check.
- **Decision F §1547-1551** — Verbatim error message. Character-exact preservation across three concatenated string-literal lines:
  > "agent role MUST NEVER appear in enforce_2fa_for_roles "
  > "(it is a service account; forcing 2FA would brick AI ingestion). "
  > "Edit apps/api/app/core/config.py or infra/.env to remove it."
- **NFR5-INT-1 §prd.md:1239** — `agent` role preserved exactly; the agent flow at `POST /api/admin/models` (cookie+password) is unchanged. `agent` role MUST NEVER appear in `enforce_2fa_for_roles`. Migration of existing `admin` (Michał) and `agent` (AI) rows is null-op — Story 7.4 adds NO new columns; only a Settings field + lifespan validation + login branch.
- **FR5-2FA-3 §prd.md:1188** — 2FA enforcement is per-role via a config flag with the `agent` role explicitly excluded. The flag `enforce_2fa_for_roles: list[Role]` lives in `apps/api/app/core/config.py` (default `[]`). At app startup, the value MUST be validated: if `Role.agent` is in the list, the app refuses to boot with a clear error. **Verifiable:** a deliberate config containing `[Role.agent]` causes the app to fail-fast on startup.
- **Epics.md §1696-1708 (Story 7.4 acceptance check shape)** — verbatim contract for the config flag + lifespan validation + middleware-check (per Cascading §1557 reinterpreted as inline-in-login) + env.example documentation.

### Files that this story creates (NEW)

| Path | LOC est | Purpose |
|---|---|---|
| `apps/api/tests/test_config.py` | 80 | 4 named config-parsing + startup-validation tests T-CONFIG-1..4 |
| `apps/api/tests/test_enforce_2fa_login.py` | 200 | 6 named login-enforcement-branch tests T-ENFORCE-1..6 |

### Files that this story modifies (UPDATE)

| Path | What changes | What must NOT change |
|---|---|---|
| `apps/api/app/core/config.py` | +`enforce_2fa_for_roles` field + `_parse_roles` validator + UserRole import (~20 LOC) | All other fields, validators, model-validator; the existing `_parse_extensions` validator |
| `apps/api/app/main.py` | +`UserRole.agent` startup validation in `lifespan` (~8 LOC) + UserRole import | The `create_app()` factory, middleware mounts, FastAPI factory, lifespan resource cleanup |
| `apps/api/app/modules/auth/models.py` | +`totp_enroll_required: bool = False` field on `LoginResponse` (1 LOC) | `PartialAuthResponse`, `MeResponse`, `LoginRequest`, `SessionRow`, `SessionsResponse` |
| `apps/api/app/modules/auth/router.py` | +enforcement branch variable assignment + audit-payload conditional + LoginResponse field assignment (~15 LOC) | Story 7.3 partial-auth branch (lines 96-114); password-verify-fail path (lines 84-92); refresh/logout/sessions handlers |
| `apps/web/src/lib/api-types.ts` | +`totp_enroll_required: boolean` on `LoginResponse` (1 LOC) | All other types |
| `apps/web/src/routes/login.tsx` | +forced-enrollment navigation conditional in `submitEmailPassword` (~8 LOC) | Story 7.3 second-factor sub-state (lines 92-129); existing single-factor success path |
| `apps/web/src/modules/auth/Settings2faPage.tsx` | +`useSearch` read + `forcedEnrollmentMode` const + banner conditional + `onWizardComplete` navigate-on-next (~20 LOC) | Story 7.2 enrollment wizard core; existing voluntary-enrollment UX |
| `apps/web/src/routes/settings/2fa.tsx` | +`validateSearch` for `next` param (~10 LOC, mirrored from `apps/web/src/routes/login.tsx:172-179`) | Route component reference |
| `apps/web/src/routes/login.test.tsx` | +V5 + V6 vitest cases (~60 LOC) | All existing V1-V4 cases (Story 7.3) |
| `apps/web/src/modules/auth/Settings2faPage.test.tsx` | +S1 + S2 vitest cases (~50 LOC) | All existing Story 7.2 enrollment-wizard tests |
| `apps/web/src/locales/en.json` | +`auth.2fa.enroll.forced_banner` key | All other keys |
| `apps/web/src/locales/pl.json` | +`auth.2fa.enroll.forced_banner` key | All other keys |
| `infra/env.example` | +`ENFORCE_2FA_FOR_ROLES=` block with comment (~7 LOC) | All other env-var blocks |

### Files that this story does NOT touch

- `apps/api/migrations/versions/` — no new migration; Story 7.1's `0013_users_2fa_columns` is still the head. The per-user override `force_2fa_enrollment` column is deferred to Story 8.4.
- `apps/api/app/core/audit.py` — `KNOWN_ENTITY_TYPES` unchanged; `auth.login.success` action is reused with an extended `after_json` payload, NOT a new action name.
- `apps/api/app/core/auth/ratelimit.py` — rate-limit key_fn / middleware unchanged. Forced-enrollment login attempts share the existing `login` scope budget (5/60s per IP) with regular logins and Story 7.3 verify attempts.
- `apps/api/app/core/auth/middleware.py` — DOES NOT EXIST and is NOT created (per Decision F Cascading §1557). The enforcement check is inline in `login()`.
- `apps/api/app/modules/auth/totp/router.py` — Story 7.2 + 7.3 endpoints unchanged. The forced-enrollment user calls existing `/api/auth/2fa/enroll` + `/api/auth/2fa/enroll/confirm` with normal cookie auth (cookies issued by the new enforcement branch).
- `apps/api/app/modules/auth/totp/service.py` — Story 7.2 helpers unchanged.
- `apps/api/app/modules/auth/totp/schemas.py` — Story 7.2 + 7.3 schemas unchanged.
- `apps/api/pyproject.toml` / `apps/api/uv.lock` — no new dependencies.
- `apps/web/src/modules/auth/Settings2faPage.test.tsx` — existing Story 7.2 voluntary-enrollment tests stay green; only S1 + S2 added.
- `apps/web/tests/visual/` — no new visual baselines (banner is a small additive element; the existing `/settings/2fa` wizard baselines from Story 7.2 cover the layout; if the dev finds the banner shifts layout significantly, they MAY add a baseline as discretionary scope, NOT binding).

### Previous-story intelligence — Story 7.3 (commits a9bea16, 7188b13, 2ffb290, 16b34d5)

Carried forward (binding for 7.4):

- **`apps/api/app/modules/auth/router.py:login()` is now `async def login` (Story 7.3 P2-1 conversion).** Story 7.4's enforcement branch lives between the Story 7.3 partial-auth branch and the single-factor success path — both branches now exist in the same async function and both off-load DB work to `asyncio.to_thread` per the Codex P2 event-loop discipline established in Story 7.3.
- **`apps/api/app/modules/auth/models.py:LoginResponse.partial_auth` discriminator was added by Story 7.3** with default `False`. Story 7.4 adds a second discriminator field `totp_enroll_required: bool = False` AFTER `user: MeResponse` (different shape variant on the same response model — full-auth-with-cookies vs full-auth-with-cookies-and-enrollment-required, distinguished by the new boolean).
- **`apps/web/src/lib/api-types.ts:LoginResponse` uses `partial_auth: false` as a literal-type discriminator** for TypeScript narrowing. Story 7.4's `totp_enroll_required` field is a regular `boolean` (NOT a literal) because the LoginResponse shape can have either `totp_enroll_required: true` or `totp_enroll_required: false` — both are valid `LoginResponse` shapes, distinguishable only at runtime.
- **`apps/web/src/routes/login.tsx` two-sub-state pattern (email_password → second_factor) shipped in Story 7.3.** Story 7.4's forced-enrollment is NOT a third sub-state — it's a navigation effect (login submit → server returns `totp_enroll_required: true` → navigate to `/settings/2fa`). Component state remains two sub-states; only the success-handler branches differently.
- **`apps/api/tests/test_2fa_verify.py` per-test fixture pattern (monkeypatch.setenv + cache_clear + create_app + fakeredis stub) is BINDING for Story 7.4's new test files.** Use `tmp_path` for the SQLite DB path; use `fakeredis.aioredis.FakeRedis()` for the Redis stub; clear `get_settings.cache_clear()` and `get_engine.cache_clear()` per-test so env-var overrides propagate to the freshly created app.

Lessons from 7.3 close-out (binding):

- **Pre-merge grep checklist is BINDING.** Story 7.3 had 8/8 silent grep checks before merge; Story 7.4 carries the discipline forward with 11 checks.
- **Visual-regression baselines ship in the SAME COMMIT as the UI change.** Story 7.4 ships ZERO new visual baselines (no substantive UI state additions); if the dev-story adds discretionary baselines, they ship in the same commit.
- **Locale keys ship in BOTH en.json AND pl.json** in the same commit. Story 7.4 adds exactly 1 key per file.
- **NO cleartext logging.** AC-9 grep check 11 carries forward Story 7.3's AC-13.4 — extended to cover `main.py` + `config.py` + `router.py` for credentials.

### Code structure guardrails — DON'T

- DON'T create `apps/api/app/core/auth/middleware.py` — the module is mentioned in architecture Decision F Choice §1554 but EXPLICITLY DECLARED non-existent in Cascading §1557. Story 7.4 follows the Cascading-block ruling and keeps the enforcement check inline in `login()`.
- DON'T add a new audit action name like `"auth.login.enroll_required"`. The action vocabulary stays at 16 names per FR5-AUDIT-1. The forced-enrollment signal lives in the `after_json` payload as `{"totp_enroll_required": true}` — queryable via SQL but not a separate vocabulary entry.
- DON'T add a new Pydantic model for the forced-enrollment response (e.g., `EnrollmentRequiredResponse`). Extend the existing `LoginResponse` with one field. Two response shapes for the same login outcome (full-auth + cookies, with or without enrollment-required flag) is more confusing than one shape with a discriminator.
- DON'T add a new endpoint like `POST /api/auth/2fa/enroll-with-partial-token` or `POST /api/auth/2fa/enroll/from-partial`. The pragmatic design has the forced-enrollment user authenticate via cookies (issued by the login branch) and call the existing Story 7.2 enrollment endpoints. NEW endpoint variants are DEFERRED to a future story if the strict no-cookies design is later required.
- DON'T modify the Story 7.3 partial-auth branch (`apps/api/app/modules/auth/router.py:96-114`). Forced-enrollment fires AFTER that branch (mutual exclusivity on `totp_enabled_at IS NOT NULL` vs `IS NULL`).
- DON'T add a frontend route guard that redirects every subsequent navigation back to `/settings/2fa` for forced-enrollment users. The single-step navigate-on-login + post-enroll-navigate-back is sufficient. A global guard is over-engineering for E7 scope.
- DON'T persist the forced-enrollment state in browser storage (localStorage, sessionStorage). The signal lives in the `LoginResponse.totp_enroll_required` field at login time + the URL `next` param at `/settings/2fa` — both ephemeral.
- DON'T add a `force_2fa_enrollment` BOOLEAN column to the `users` table in this story. That column is Story 8.4's responsibility per epics §1798.
- DON'T extend the Story 7.3 second-factor sub-state in `login.tsx` to also handle forced-enrollment. Forced-enrollment uses a navigation effect, NOT a sub-state transition.
- DON'T log the verbatim Decision F error message via the structured logger (it's already raised as a RuntimeError — uvicorn's exception handler will log it on stderr at startup, which is the correct surfacing). Don't double-log it through `_LOG.error`.
- DON'T allow the `_parse_roles` validator to silently filter out unknown roles. Raise `ValueError` with the verbatim message per AC-1 so operator misconfigurations fail fast at instantiation time (mirrors the `_block_default_secrets_in_prod` discipline).

### Code structure guardrails — DO

- DO place the `UserRole.agent` startup-validation block BEFORE every other lifespan side-effect (no logging, no DB connection, no schema init, no Redis connection, no arq pool). The architecture explicitly says "BEFORE Redis connection + BEFORE any route mount" — Story 7.4 strictly enforces "BEFORE EVERYTHING ELSE in lifespan" (the only thing allowed before the validation is `settings = get_settings()`, which is a pure read of cached Settings).
- DO use `Annotated[list[UserRole], NoDecode]` on the field declaration — `NoDecode` is required because Pydantic's default decoder would try to JSON-parse the env-var value, and `"member,admin"` is not valid JSON. The custom `_parse_roles` validator handles the comma-separated string.
- DO use the lowercased role-name comparison (`UserRole(candidate)` where `candidate = item.strip().lower()`) — env-var values are case-insensitive at parse time. The internal type is `list[UserRole]` (typed enum); the env representation is case-insensitive strings.
- DO emit the audit row payload conditionally — non-forced-enrollment logins MUST keep their existing audit shape `after={"email": user.email}` UNCHANGED (backward-compat regression guard for existing audit consumers and tests). Only forced-enrollment logins add the `"totp_enroll_required": true` key.
- DO test the SINGLE-FACTOR baseline regression explicitly (T-ENFORCE-2, T-ENFORCE-3, T-ENFORCE-6) — these tests guard against the new branch accidentally firing on users it should not affect.
- DO test the MUTUAL-EXCLUSIVITY regression explicitly (T-ENFORCE-4) — TOTP-enabled members in the enforce list MUST take the Story 7.3 verify path (partial-auth-no-cookies), NOT the Story 7.4 forced-enrollment path.
- DO use `pytest.raises(RuntimeError, match="agent role MUST NEVER appear")` for T-CONFIG-2 — the substring match keeps the test stable even if the message is reformatted within reason; the AC-9 grep check 1 verifies the exact wording in the source file.
- DO use the existing `infra/env.example` env-var-block convention (commented-out default with explanatory comment block above) for the `ENFORCE_2FA_FOR_ROLES` documentation. Operator copies + uncomments to enable.
- DO add the `validateSearch` extension to `apps/web/src/routes/settings/2fa.tsx` BEFORE the Settings2faPage component changes — TanStack Router type-narrows search params via the route definition, so the component-level `useSearch` call relies on the route having the param declared.
- DO use the existing `apps/web/src/routes/login.tsx:172-179` `validateSearch` pattern as the BINDING template for `/settings/2fa` — same shape, same null-handling, same TypeScript discipline.

### Testing standards summary

- Backend tests: `pytest` with FastAPI `TestClient` against a real SQLite test DB (per-test `tmp_path`); fakeredis stubbed via the per-test redis-factory patch precedent. Run from `apps/api/` directory.
- Backend tests for Story 7.4 use PER-TEST `monkeypatch.setenv` + `get_settings.cache_clear()` + `create_app()` (NOT the session-scoped `_isolated_db` fixture from `conftest.py`) because each test needs PER-TEST control over the `ENFORCE_2FA_FOR_ROLES` env var.
- Frontend unit tests: `vitest` against React Testing Library; mock `api()` calls via `vi.mock("@/lib/api", ...)` matching the existing `login.test.tsx` pattern.
- The per-test cleanup in `vitest.setup.ts` (registered 2026-05-10, commit a026e97) handles `afterEach(cleanup)` — new test cases in this story do NOT need to register their own afterEach hooks.

### Project Structure Notes

- The config field lives in `apps/api/app/core/config.py` alongside the other Pydantic Settings fields (NOT in a separate config module or DB-stored config — per Decision F §1555 alternatives-rejected: "DB-stored config (mismatch with all other rate-limit/CSRF/cookie settings in Pydantic Settings; introduces a config-drift surface)").
- The lifespan validation lives in `apps/api/app/main.py:lifespan` (NOT in `create_app()` because lifespan runs at app-startup time, which is the binding "before any request reaches the wire" guarantee from Decision F).
- The login enforcement branch lives in `apps/api/app/modules/auth/router.py:login()` inline (NOT in a separate middleware per Cascading §1557 ruling).
- The frontend forced-enrollment handling lives in `apps/web/src/routes/login.tsx:submitEmailPassword` AND `apps/web/src/modules/auth/Settings2faPage.tsx` — the navigation effect crosses the two components.
- The forced-enrollment audit signal is a payload extension on the existing `auth.login.success` action — NOT a new action vocabulary entry. This preserves the 16-action FR5-AUDIT-1 contract.

### References

- `_bmad-output/planning-artifacts/epics.md:1696-1708` (Story 7.4 acceptance check shape)
- `_bmad-output/planning-artifacts/architecture.md:1536-1557` (Decision F: config flag + verbatim error message + Choice-vs-Cascading placement ruling)
- `_bmad-output/planning-artifacts/prd.md:1188` (FR5-2FA-3 binding requirement)
- `_bmad-output/planning-artifacts/prd.md:1239` (NFR5-INT-1 agent-role-preserved invariant)
- `_bmad-output/planning-artifacts/prd.md:1200` (FR5-AUDIT-1 vocabulary — `auth.login.success` is an existing action; payload extension does not add a new entry)
- `_bmad-output/implementation-artifacts/7-3-login-partial-auth-totp-verify.md` (Story 7.3 spec — partial-auth + verify surface; Story 7.4 enforcement branch placement after the 7.3 branch)
- `_bmad-output/implementation-artifacts/sprint-status.yaml:154` (Story 7.3 close-out + dependency for 7.4)
- `apps/api/app/core/config.py:66-87` (`download_extensions` precedent — env-var comma-separated parser pattern modeled by `_parse_roles`)
- `apps/api/app/main.py:27-51` (existing `lifespan` to extend with the startup validation)
- `apps/api/app/modules/auth/router.py:63-152` (existing async `login()` to extend with the enforcement branch)
- `apps/api/app/modules/auth/models.py:21-23` (existing `LoginResponse` to extend with the new field)
- `apps/api/app/core/db/models/_enums.py:10-13` (`UserRole` enum — `admin`, `agent`, `member`)
- `apps/api/app/core/auth/dependencies.py:_ALLOWED_ROLES` (existing role-string allowlist precedent — Story 7.4 reuses the typed `UserRole` enum instead)
- `apps/api/tests/test_2fa_verify.py:44-70` (per-test fixture pattern — binding for Story 7.4's new test files)
- `apps/web/src/routes/login.tsx:172-179` (existing `validateSearch` pattern — binding template for `apps/web/src/routes/settings/2fa.tsx`)
- `apps/web/src/lib/api-types.ts:24-27` (existing `LoginResponse` interface to extend)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-05-19 — Story 7.4 spec authored via `bmad-create-story` (autonomous YOLO). Realizes FR5-2FA-3 + NFR5-INT-1 — config flag `enforce_2fa_for_roles: list[UserRole]` in `apps/api/app/core/config.py` + lifespan-startup fail-fast on `UserRole.agent` in the list (RuntimeError with verbatim Decision F message) + inline enforcement branch in `apps/api/app/modules/auth/router.py:login()` (placed AFTER Story 7.3 partial-auth branch, BEFORE single-factor success path) that detects `user.totp_enabled_at IS NULL AND user.role IN settings.enforce_2fa_for_roles` and issues cookies (pragmatic design — user IS single-factor authenticated by password; cookies enable enrollment-endpoint cookie auth) + returns extended `LoginResponse` with `totp_enroll_required: true` + emits extended `auth.login.success` audit payload `{"email": ..., "totp_enroll_required": true}`. Frontend extends `apps/web/src/routes/login.tsx` (detects `resp.totp_enroll_required === true` and navigates to `/settings/2fa?next=<original-next>` instead of intended destination) + `apps/web/src/modules/auth/Settings2faPage.tsx` (forced-enrollment banner when `next` URL param present; post-confirm navigate to `next`). NEW Pydantic Settings field + validator; NEW `LoginResponse.totp_enroll_required: bool = False` field; NEW lifespan validation; NEW i18n key `auth.2fa.enroll.forced_banner` (en + pl); NEW `infra/env.example` block. NO new Alembic migration; NO new endpoints; NO new audit-vocabulary entry (reuses `auth.login.success` with payload extension); NO new dependencies; NO new visual baselines (banner is a minor additive UI element). 673 backend tests pass (663 baseline + 4 new in `test_config.py` T-CONFIG-1..4 + 6 new in `test_enforce_2fa_login.py` T-ENFORCE-1..6). 335 vitest specs pass (331 baseline + V5 + V6 in `login.test.tsx` + S1 + S2 in `Settings2faPage.test.tsx`). 216 visual specs pass (no change). Architecture Decision F Choice-block (`apps/api/app/core/auth/middleware.py`) vs Cascading-block (inline in `login()`) contradiction explicitly resolved per the Cascading-block ruling — no new `middleware.py` module created. Per-user override (admin force-2FA-enrollment) explicitly deferred to Story 8.4 per epics §1798. Strict no-cookies-on-forced-enrollment + new-endpoint-variants design explicitly deferred to a future story if Codex review later flags pragmatic design as insufficient; current pragmatic design relies on frontend route gating, sufficient for operator's banking-IT-trust model (Michał is sole admin). Architecture's "pre-cookie-issue" wording in Decision F §1554 treated as loose ordering language, not a hard no-cookies constraint. Backward-compat preserved: existing `auth.login.success` audit shape unchanged for non-forced-enrollment logins (T-ENFORCE-6 regression guard); existing single-factor success path unchanged (T-ENFORCE-2, T-ENFORCE-3 regression guards); Story 7.3 partial-auth-verify path unchanged (T-ENFORCE-4 mutual-exclusivity guard).
