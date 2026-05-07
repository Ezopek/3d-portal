# Auth refresh token flow - design review

**Date:** 2026-05-07
**Reviewer:** Codex
**Reviewed document:** `docs/superpowers/specs/2026-05-07-auth-refresh-token-flow-design.md`
**Related context:** current `apps/api/app/modules/auth/*`, `apps/web/src/lib/api.ts`, `apps/web/src/shell/AuthContext.tsx`, `apps/api/app/modules/sot/router.py`, current Alembic head `0008`

## Verdict

The design is directionally good and much stronger than the current
`localStorage` bearer-token flow. The main choices - httpOnly cookies, short
access lifetime, opaque hashed refresh tokens, refresh rotation, server-side
revocation, and a sessions UI - line up well with OWASP session guidance and
OAuth refresh-token replay guidance.

I would not treat it as implementation-plan-ready yet. The rough edges are not
mostly visual polish; they are a few contract gaps that can break "stay signed
in" after ten minutes, weaken stolen-token detection, or leave parts of the API
outside the auth boundary the design appears to promise.

Recommended decision before planning: **revise the design, then write the
implementation plan**.

## Findings

### P1 - Expired access cookies may force logout instead of refresh

The client only refreshes on `401 {detail: "access_expired"}`. But the cookie
table gives `portal_access` a 10-minute TTL. If the browser actually expires and
drops that cookie, the next `/api/auth/me` or protected API call will produce
`missing_access`, not `access_expired`. The current design says every other 401
means force-relogin, so a normal "come back after lunch" flow can become a login
prompt even though the 30-day refresh cookie is still present.

Pick one explicit model:

- make `missing_access` refreshable on browser/API calls, with `/auth/refresh`
  deciding whether a refresh cookie exists,
- keep the access cookie physically longer than the JWT and rely on JWT `exp`
  for `access_expired`,
- or let `/auth/me` perform a refresh-aware session check through a separate
  endpoint such as `/auth/session`.

The first option is probably the smallest change. It needs a retry guard so truly
anonymous users do not loop forever.

### P1 - The 30-second grace window hands the active refresh to a stolen old token

The multi-tab grace branch says that presenting a recently rotated refresh token
returns cookies bound to the current active descendant. That is good for benign
tab races, but it also means an attacker with the old refresh token can refresh
successfully during the grace window and receive the new active session.

This directly softens the replay-detection property that rotation is meant to
give. RFC 9700 recommends rotation because replay of an invalidated refresh
token should reveal a breach and revoke the active token. A grace window can be a
reasonable UX tradeoff, but the spec should name the tradeoff and constrain it.

Safer options:

- remove server-side grace and rely on the frontend singleton plus
  `BroadcastChannel` for cross-tab coordination,
- shrink grace sharply and require matching `user_agent` and recent IP bucket,
- return the descendant only for the same client fingerprint and log mismatches
  as suspicious without issuing the active token,
- or accept occasional tab-level relogin instead of making old refresh material
  temporarily valid.

### P1 - SQLite concurrency guarantee is not true as written

The spec says concurrent refreshes are naturally ordered by SQLite with
`BEGIN IMMEDIATE` via SQLAlchemy `isolation_level="IMMEDIATE"` if needed. In the
current API environment, SQLAlchemy rejects that engine isolation level for
SQLite; valid values are `READ UNCOMMITTED`, `SERIALIZABLE`, and `AUTOCOMMIT`.

This matters because default deferred transactions can let two requests read the
same active row before either writes. The implementation needs a concrete lock
strategy, for example:

- explicitly issue `BEGIN IMMEDIATE` at the start of the refresh transaction,
- use a small helper for refresh-token transactions and test concurrent calls,
- add a partial unique index so there can be only one active token per family:
  `UNIQUE (family_id) WHERE revoked_at IS NULL`.

Without that unique active-family invariant, the "active descendant leaf" can
become ambiguous after a bug or race.

### P1 - The app auth boundary is unresolved for catalog reads and file content

The design says every call sends cookies and "auth is server-decided", but the
current SoT read router has no auth dependency on `/api/categories`,
`/api/tags`, `/api/models`, `/api/models/{id}`, `/api/models/{id}/files`, or
`/api/models/{id}/files/{file_id}/content`.

That may be intentional because the portal is also behind nginx `auth_basic`.
If so, say it plainly: app auth protects admin/session surfaces, while catalog
read APIs remain perimeter-protected by nginx. If not, the design must add
`current_user` to read endpoints.

There is one extra wrinkle: the share flow currently returns direct file URLs
under `/api/models/.../content`. If file content becomes app-authenticated, share
downloads and images need a share-aware file endpoint or signed content URLs.
Otherwise logout will not mean what users expect for direct API/file access.

### P1 - Migration revision number is stale

The spec names the new migration `0006_refresh_tokens`, but the repository is
already at Alembic head `0008`. The implementation plan should create the next
revision after `0008`, likely `0009_refresh_tokens`, and update any migration
test names accordingly.

### P2 - CSRF design is good, but should be less single-layer

`SameSite=Strict` plus a custom header is a reasonable SPA defense when CORS is
not permissive. OWASP explicitly supports custom headers for AJAX/API-style CSRF
defense and recommends explicit SameSite cookie attributes.

The spec should still tighten three points:

- state that CORS must remain absent or same-origin-only for credentialed
  requests; a permissive future CORS change would weaken the static-header
  check,
- add `Origin` and/or Fetch Metadata checks (`Sec-Fetch-Site`) as defense in
  depth for mutating `/api/*` requests,
- audit direct `fetch` callsites, especially multipart upload
  `useUploadFile.ts`, because they will not automatically inherit the wrapper's
  `X-Portal-Client` header or refresh retry.

The `/api/share/*` exemption is harmless today because it is GET-only, but the
reasoning "no cookie surface" is not quite right: `portal_access` with
`Path=/api` is still sent to `/api/share/*` by authenticated browsers.

### P2 - Pure sliding refresh should have an explicit absolute cap or deviation note

The design gives refresh tokens a 30-day sliding TTL and no absolute session
lifetime. That meets the stated "bounded for inactive sessions" goal, but OWASP
session guidance also recommends an absolute timeout independent of activity.

For a household portal, indefinite active sessions may be an acceptable product
choice. It should be documented as a conscious deviation, or the schema should
track `family_issued_at` / `absolute_expires_at` and cap a family at something
like 90 or 180 days.

### P2 - Secure cookies will break direct HTTP access paths

Production defaults to `COOKIE_SECURE=true`, which is correct for
`https://3d.ezop.ddns.net`. But the production compose file still exposes the
web container on plain HTTP port `8090` for direct LAN access. Secure cookies
will not work there in real browsers.

The spec should decide whether direct `http://.190:8090` access is no longer
supported after this change, or whether the homelab/dev path needs its own
explicit `COOKIE_SECURE=false` environment. The same concern applies to tests:
depending on the client base URL, secure cookies may not be sent back unless the
test settings disable `cookie_secure` or use an HTTPS base URL.

### P2 - Access cookie path claims are slightly overconfident

Scoping `portal_refresh` to `/api/auth` is a strong choice. Scoping
`portal_access` to `/api` is also reasonable, but it is still sent to all
`/api/*` routes, including anonymous share routes and direct file-content URLs.
Path scoping reduces accidental exposure; it is not an authorization boundary.

The design should avoid saying `/api/share/*` has "no cookie surface" unless the
access cookie path is narrowed further or share routes are moved outside
`/api`.

### P2 - Logout and sessions endpoints need idempotent edge behavior

The endpoint table is good, but the design should define what happens when:

- `/auth/logout` has a valid access cookie but no refresh cookie,
- `/auth/logout` is called after another tab already cleared/revoked the family,
- `/auth/sessions` has an access cookie but cannot match the current refresh
  cookie,
- the user manually revokes the current family from `/settings/sessions`.

For UX, logout should almost always clear cookies and return success even if the
server-side session row is already gone. Users should not see an error while
trying to leave.

### P2 - Retry semantics need to cover non-JSON and non-idempotent calls

The `api()` wrapper retry sketch works for JSON requests. The portal also has
multipart upload and binary/download/image paths. Mutating upload calls need to
set the CSRF header and either use the same refresh-aware path or show a clean
"session expired, retry upload" error before sending a large body.

The implementation plan should include tests for:

- JSON mutation after access expiry,
- multipart upload after access expiry,
- no retry loop when `/auth/refresh` itself fails,
- only one replay of the original request.

### P2 - First-paint auth UX needs a true tri-state

The spec correctly notes that `isAdmin` becomes asynchronous. Carry that through
all shell components:

- `AuthGate` should check `isLoading` before `isAuthenticated`,
- protected routes should show a small app-shell spinner/skeleton rather than
  flickering to the anonymous/login state,
- `UserMenu` should show the real display name/email from `/auth/me`, not a
  hardcoded role label,
- session-expired UX should preserve the return path after login.

This is less about aesthetics and more about trust. Auth UI that briefly lies on
first paint feels broken even when the backend is correct.

### P2 - Rate limiting should probably move closer to this slice

The spec lists rate limiting as a non-goal. That is understandable for a small
homelab, but `/auth/login` and `/auth/refresh` are now the most security-relevant
endpoints in the app. At minimum, the implementation plan should add structured
audit fields that make later rate limiting straightforward (`ip`, normalized
user agent, user id/family id when known) and create a concrete follow-up issue.

If the slice stays small, this can remain a documented risk. I would not leave
it as an unnamed backlog idea.

### P3 - Audit volume may grow more than expected

With a 10-minute access token and reactive refresh, active users can emit
`auth.refresh.success` many times per day. In a household portal this is probably
fine, but the audit log is persistent and the cleanup job intentionally does not
touch it.

Decide whether every successful refresh is worth a permanent audit row, or
whether successful refreshes should be structured logs while login/logout/reuse
remain audit-log events.

### P3 - Sessions screen UX is right, but needs mobile and naming details

The sessions UI is a good addition. To feel polished, the spec should add:

- mobile layout behavior for the sessions table,
- copy for unknown device / unknown IP,
- "current session" protection so the primary action is not accidentally
  revoking the device currently in hand,
- relative and absolute time display on hover/focus,
- localized strings in the existing flat `apps/web/src/locales/{en,pl}.json`
  files.

## What looks good

- Moving tokens out of `localStorage` is the right call. `httpOnly`, `Secure`,
  and `SameSite=Strict` cookies match current session-management guidance.
- Opaque refresh tokens stored as hashes are a good fit here. A DB dump should
  not be enough to replay refresh tokens.
- Refresh rotation with family-level reuse detection is the right security
  primitive for stolen refresh material.
- The access-token TTL of 10 minutes is a sensible compromise if refresh is
  reliable and UX is quiet.
- Per-session logout, logout-all, and a sessions screen are exactly the right
  user-facing controls for long-lived sessions.
- Deleting `decodeJwtRole` and deriving role from `/auth/me` fixes the current
  expired-token UI bug at the right layer.

## Suggested design revisions

Before planning implementation, tighten these decisions:

1. Define the refresh behavior for `missing_access` vs `access_expired`.
2. Rework or explicitly constrain the server-side grace window.
3. Specify the SQLite transaction mechanism and add a unique active-family
   invariant.
4. Decide whether catalog read/file APIs are app-authenticated or only
   nginx-perimeter-protected; update share-file serving accordingly.
5. Update the migration revision to current Alembic head.
6. Add Origin/Fetch Metadata/CORS assumptions to the CSRF section.
7. Decide whether long-lived sessions need an absolute lifetime.
8. Document the HTTPS-only operational consequence of `Secure` cookies.
9. Make `AuthGate`, `UserMenu`, uploads, and session-expired UX part of the
   implementation plan, not incidental cleanup.

## References checked

- OWASP Session Management Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP Cross-Site Request Forgery Prevention Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- RFC 9700, Best Current Practice for OAuth 2.0 Security:
  https://www.rfc-editor.org/rfc/rfc9700
