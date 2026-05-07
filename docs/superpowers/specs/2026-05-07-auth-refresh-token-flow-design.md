# Auth refresh token flow — design

Status: design approved, awaiting implementation plan.
Date: 2026-05-07.
Driver: long-lived sessions without exposing tokens to JS, with detection of stolen-token reuse.

## Problem

Current auth (`apps/api/app/modules/auth/router.py`, `apps/web/src/lib/auth.ts`):

- 30-min access JWT, no refresh, no rotation.
- Token lives in `localStorage` and is sent as `Authorization: Bearer …`.
- `decodeJwtRole` reads role from JWT payload without checking `exp`. UI uses that synchronous read for `isAdmin`, so admin-only tabs render even when the JWT has expired — clicking them produces a confusing 401 (e.g. `/api/admin/audit-log` → "Missing bearer token") instead of forcing re-login.
- No way to reissue without full re-login. No way to revoke a session remotely. No audit trail of token issuance/rotation.

We want the strongest practical model for a household portal behind nginx auth_basic / DDNS:

- **No tokens readable from JS.** XSS cannot exfiltrate session material.
- **Long-lived sessions** without daily re-login, but bounded for inactive sessions.
- **Detection of stolen-refresh reuse** with automatic family revoke.
- **Per-session logout** + "logout everywhere" + active-sessions UI.

## Decisions (captured during brainstorming)

| # | Decision | Value |
|---|---|---|
| 1 | Storage of both tokens | `httpOnly` Secure cookies, no localStorage |
| 2 | Access TTL | 10 minutes |
| 3 | Refresh TTL | 30 days, sliding (resets on rotation) |
| 4 | Refresh rotation | Yes, every refresh issues a new opaque secret |
| 5 | Reuse detection | Yes — presenting a revoked-and-not-rotated refresh burns the whole family |
| 6 | Multi-tab grace window | 30 s server-side; presenting a token revoked with `reason=rotated` within 30 s returns the current family token |
| 7 | CSRF strategy | `SameSite=Strict` cookies + custom header `X-Portal-Client: web` checked by middleware on all mutating endpoints |
| 8 | Logout scope | Per-session by default, plus explicit "logout everywhere", plus `/settings/sessions` UI for granular revoke |
| 9 | Refresh trigger on client | Pure reactive — fetch wrapper detects 401 + body `detail: "access_expired"`, calls `/auth/refresh`, retries original |

## Non-goals (out of scope for this project)

- Per-request revocation of access JWT (we accept "stolen access works max 10 min").
- Audit-log entry for every authenticated request (only login/refresh/logout/revoke lifecycle is audited).
- Rate-limiting on `/auth/login` or `/auth/refresh` (separate backlog item; logged as risk below).
- Passkeys / 2FA / WebAuthn (separate project).
- "New device" notifications — DB has the data (`last_used_at`, `ip`, `user_agent`), backlog only.
- Client-side `BroadcastChannel` cross-tab refresh broadcast (server-side grace + per-tab idempotent refresh is enough; can add later if UX warrants it).

## Architecture

### Cookie design

| Cookie | Type | TTL | `Path` | `SameSite` | `Secure` | `httpOnly` | Contents |
|---|---|---|---|---|---|---|---|
| `portal_access` | JWT (HS256) | 10 min | `/api` | `Strict` | env-conditional | yes | `sub`, `role`, `iat`, `exp`, `jti` |
| `portal_refresh` | opaque random 256-bit (`secrets.token_urlsafe(32)`) | 30 days sliding | `/api/auth` | `Strict` | env-conditional | yes | reference into `refresh_tokens` table |

Three explicit choices:

1. **Path scoping.** `portal_refresh` is scoped to `/api/auth` so it never leaves the auth surface — proxies, traces, error reports outside `/api/auth/*` cannot leak it. `portal_access` is scoped to `/api` so it does not leak to the `/share/*` static surface.
2. **Refresh is opaque, not a JWT.** Refresh tokens must hit the DB anyway (rotation, revoke, family detection). Making them JWTs adds key management and a redundant `exp` without benefit. We store `SHA-256(secret)`, never the raw value — a DB dump cannot be replayed.
3. **Access is a JWT.** Required for the auth dependency to validate per request without a DB hit. There is no per-`jti` blocklist — `JWT_SECRET` rotation is the only global "revoke now" lever, and that is acceptable given the 10-min ceiling.

### `Secure` flag in dev

`Secure` cookies are not transmitted over plain HTTP, which breaks the local Vite (`localhost:5173`) ↔ FastAPI (`localhost:8090`) flow. Resolution:

- New setting `cookie_secure: bool = True` in `app/core/config.py`.
- Local dev `.env` sets `COOKIE_SECURE=false`. Production `.env` keeps the default.
- `set_cookie(...)` calls pass `secure=settings.cookie_secure`.
- `SameSite=Strict` works in both: dev is same-site between Vite and FastAPI on `localhost`; prod is same-site under `3d.ezop.ddns.net`.

### Database schema

New table created via Alembic migration `0006_refresh_tokens`. The production DB is SQLite (`infra/docker-compose.yml` mounts `sqlite:////data/state/portal.db`), so column types follow the project pattern from migration `0005`: `sa.Uuid(as_uuid=True)`, `sa.DateTime()`, `sa.String()`. UUIDs are generated in Python (`uuid.uuid4()`) at insert time — there is no server-side default.

```
refresh_tokens
  id              UUID (sa.Uuid)        PK, generated in Python
  user_id         UUID (sa.Uuid)        NOT NULL, FK → user.id, ON DELETE CASCADE
  family_id       UUID (sa.Uuid)        NOT NULL  -- shared across the rotation chain
  token_hash      String                NOT NULL, UNIQUE  -- hex(SHA-256(secret))
  issued_at       DateTime              NOT NULL, set in Python at insert
  expires_at      DateTime              NOT NULL  -- issued_at + 30d
  replaced_at     DateTime              NULL      -- when this token was rotated
  replaced_by_id  UUID (sa.Uuid)        NULL, FK → refresh_tokens.id
  revoked_at      DateTime              NULL
  revoke_reason   String                NULL  -- enforced via CHECK constraint
  last_used_at    DateTime              NULL      -- bumped each refresh
  ip              String                NULL      -- IP as text (SQLite has no INET)
  user_agent      String                NULL      -- truncated to 500 chars in app code

CHECK CONSTRAINT  revoke_reason IS NULL OR revoke_reason IN
                    ('rotated','logout','logout_all','reuse_detected','manual')
INDEX ix_refresh_tokens_user_active   ON (user_id) WHERE revoked_at IS NULL
INDEX ix_refresh_tokens_family        ON (family_id)
```

SQLite supports both partial indexes and `CHECK` constraints, so the migration is portable to PostgreSQL later (when/if we move) without changing column types — only `String` → `INET` for `ip` would be worth tightening.

Cleanup: a daily worker job `cleanup_refresh_tokens` (arq scheduled task) deletes rows where
`(revoked_at IS NOT NULL AND revoked_at < now - 7 days) OR (expires_at < now - 7 days)`. Audit-log lifecycle events live separately in `audit_log` and are not affected by this cleanup.

### Refresh rotation algorithm

`POST /api/auth/refresh` reads `portal_refresh` cookie and:

1. If cookie absent → 401 `{"detail": "no_refresh"}`.
2. Look up by `token_hash = sha256(secret)`. If not found → 401 `{"detail": "invalid_refresh"}`.
3. If `expires_at < now()` → 401 `{"detail": "refresh_expired"}`.
4. If `revoked_at IS NOT NULL`:
   - If `revoke_reason = 'rotated'` AND `now() - replaced_at < 30 s`:
     - **Grace path.** Look up the active descendant in the family (the leaf, where `revoked_at IS NULL`). If found → reissue cookies bound to that descendant; do not rotate again. If no active descendant exists in this 30-s window → 401 `{"detail": "force_relogin"}` (race lost, treat as anomalous).
   - Else:
     - **Reuse detected.** Update all rows in the family to `revoked_at = now(), revoke_reason = 'reuse_detected'`. Emit `auth.refresh.reuse_detected` audit event with `user_id`, `family_id`. Return 401 `{"detail": "force_relogin"}`.
5. Happy path:
   - Generate `new_secret = secrets.token_urlsafe(32)`.
   - Insert new row with same `family_id`, `token_hash = sha256(new_secret)`, `expires_at = now() + 30 d`, `last_used_at = now()`, `ip`, `user_agent`.
   - Update old row: `revoked_at = now(), revoke_reason = 'rotated', replaced_at = now(), replaced_by_id = new.id`.
   - Issue new access JWT (`exp = now + 10 m`).
   - Set both cookies. Emit `auth.refresh.success`. Return `200 {"user": MeResponse}`.

All read+update steps run inside a single transaction. SQLite serializes write transactions globally (`BEGIN IMMEDIATE` per SQLAlchemy with `isolation_level="IMMEDIATE"` on the engine if not already), so concurrent refreshes are naturally ordered — the second one will see the first one's `revoked_at` and either land in the grace branch or trip reuse detection, both of which are correct outcomes. No explicit row lock needed at this scale.

### Endpoints

| Method + path | Status | Description |
|---|---|---|
| `POST /api/auth/login` | changed | Verifies password. Creates a new family with one fresh refresh row. Sets both cookies. Returns `{user: MeResponse}`. No tokens in body. |
| `POST /api/auth/refresh` | new | Algorithm above. |
| `POST /api/auth/logout` | changed | Revokes current refresh's family with `reason='logout'`. Clears both cookies (`Max-Age=0`). 204. |
| `POST /api/auth/logout-all` | new | Revokes all of the user's families with `reason='logout_all'`. Clears cookies. 204. |
| `GET /api/auth/me` | changed | Reads access from cookie. Same response shape as today. |
| `GET /api/auth/sessions` | new | Returns `[{family_id, last_used_at, ip, user_agent, is_current}]` — one entry per family (not per token in the chain). |
| `DELETE /api/auth/sessions/{family_id}` | new | Revokes the named family with `reason='manual'`. 403 if the family does not belong to the calling user. If the family is the current one, the response also clears cookies. |

Granularity choice: sessions UI is per-family because users think "the tablet in the living room", not per-token in the rotation chain.

### Auth dependency rewrite (`app/core/auth/dependencies.py`)

`HTTPBearer` is removed. The dependency reads `request.cookies.get("portal_access")` and decodes the JWT. Error bodies use stable `detail` codes the client can branch on:

| Condition | Status | `detail` |
|---|---|---|
| No cookie | 401 | `missing_access` |
| JWT expired | 401 | `access_expired` |
| JWT invalid signature / malformed | 401 | `invalid_access` |
| Role not in allowed set | 403 | `forbidden_role` |
| Admin required and role ≠ admin | 403 | `admin_required` |

Client only triggers reactive refresh on `access_expired`. The other 401 codes mean force-relogin.

### CSRF middleware (`app/core/auth/csrf.py`)

```python
@app.middleware("http")
async def csrf_guard(request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        path = request.url.path
        if path.startswith("/api/") and not path.startswith("/api/share/"):
            if request.headers.get("X-Portal-Client") != "web":
                return JSONResponse({"detail": "csrf_required"}, status_code=403)
    return await call_next(request)
```

- `GET`/`HEAD`/`OPTIONS` are exempt by RFC 9110 semantics — they must be safe.
- `/api/share/*` is exempt because it is anonymous and has no cookie surface to steal.
- `/api/auth/login` and `/api/auth/refresh` are NOT exempt — login-CSRF (session fixation) and refresh-CSRF are real attacks. The SPA fetch wrapper sets the header on every call, so this is invisible to clients.

### Audit events

Action strings (no schema change; `audit_log.action` is `TEXT`):

| Action | Emitted by | Notes |
|---|---|---|
| `auth.login.success` | existing | unchanged |
| `auth.login.fail` | existing | unchanged |
| `auth.refresh.success` | new | `actor_user_id`, `after={family_id}` |
| `auth.refresh.reuse_detected` | new | `actor_user_id=null`, `after={family_id, ip, user_agent}` |
| `auth.logout` | changed | `actor_user_id`, `after={family_id}` |
| `auth.logout_all` | new | `actor_user_id`, `after={revoked_count}` |
| `auth.session.revoked` | new | manual revoke from `/settings/sessions`; `after={family_id}` |

### Frontend changes

#### `apps/web/src/lib/api.ts` (rewrite)

- `authenticated` parameter removed. Every call sends cookies; auth is server-decided. ~30 callsites simplify (token-marker boilerplate disappears).
- `credentials: "include"` set on every fetch.
- Header `X-Portal-Client: web` always set.
- Reactive refresh:

```ts
let response = await doFetch();
if (response.status === 401) {
  const body = await response.clone().json().catch(() => ({}));
  if (body?.detail === "access_expired") {
    const ok = await refreshAccessToken();   // singleton, see below
    if (ok) response = await doFetch();
  }
}
```

#### `apps/web/src/lib/refresh.ts` (new)

Singleton in-flight promise — without it, a dashboard mount fires 4–5 admin queries in parallel, all hit 401, and 4–5 concurrent `/auth/refresh` calls race the 30-s grace.

```ts
let inFlight: Promise<boolean> | null = null;

export function refreshAccessToken(): Promise<boolean> {
  if (inFlight) return inFlight;
  inFlight = (async () => {
    try {
      const r = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "X-Portal-Client": "web" },
      });
      return r.ok;
    } finally {
      inFlight = null;
    }
  })();
  return inFlight;
}
```

#### `apps/web/src/lib/auth.ts` — deleted

Three callsites migrated:

- `routes/login.tsx`: `writeToken(...)` → on successful login, `queryClient.invalidateQueries({queryKey: ["auth", "me"]})` and `navigate("/")`.
- `shell/UserMenu.tsx`: `clearToken()` → `await api("/auth/logout", {method: "POST"})`.
- `shell/AuthContext.tsx`: rewritten (below).

#### `apps/web/src/lib/jwt.ts` — deleted

`decodeJwtRole` is no longer reachable — JS cannot read the cookie. Role flows through `/auth/me`.

#### `apps/web/src/shell/AuthContext.tsx` (rewrite)

```ts
export function AuthProvider({ children }: { children: ReactNode }) {
  const meQuery = useQuery<MeResponse, ApiError>({
    queryKey: ["auth", "me"],
    queryFn: () => api<MeResponse>("/auth/me"),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const value = useMemo<AuthState>(() => {
    if (meQuery.isLoading) return { ...ANONYMOUS, isLoading: true };
    if (meQuery.isError) return ANONYMOUS;
    const u = meQuery.data!;
    return {
      user: u,
      role: u.role,
      isAdmin: u.role === "admin",
      isMember: u.role === "member",
      isAdminOrAgent: u.role === "admin" || u.role === "agent",
      isAuthenticated: true,
      isLoading: false,
    };
  }, [meQuery.isLoading, meQuery.isError, meQuery.data]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
```

Consequence: `isAdmin` is asynchronous on first paint. `AuthGate.tsx` must show a spinner while `isLoading`, not treat absent role as "anonymous". Every callsite reading `isAdmin` must be audited so admin-only UI renders nothing (or a skeleton) during loading rather than briefly flashing "non-admin" state. The implementation plan covers this audit.

#### Sessions screen (`/settings/sessions`)

- Lazy-loaded route. Link from `UserMenu.tsx` next to "Logout".
- Hooks: `useSessions()` (`GET /auth/sessions`), `useRevokeSession(family_id)` (`DELETE /auth/sessions/{id}`), `useLogoutAll()` (`POST /auth/logout-all`).
- Layout: a table with `Last used` (relative time), `Device` (parsed user-agent — use existing `ua-parser-js` if already a dep, otherwise raw string truncated to 50 chars; the implementation plan resolves this), `IP`, `is_current` badge, `Revoke` button. Above the table: `Logout from all other devices` button (disabled when there is no "other").
- Revoking the current session redirects to `/login`. Revoking another session refetches the list.
- Visual regression test for the screen (Playwright) per project standard for UI changes.

#### Migration of existing localStorage tokens

A one-shot effect runs on `AuthProvider` mount:

```ts
useEffect(() => {
  localStorage.removeItem("portal.token");
  localStorage.removeItem("portal.token.exp");
}, []);
```

After the deploy, the first page load of every existing user wipes the stale keys. The effect is idempotent and cheap, so it can stay indefinitely; we will remove it whenever code-level dead-code cleanup happens next.

## Operational impact

### nginx (`infra/nginx-180/3d-portal.conf`)

Default nginx behavior preserves `Cookie` request headers and `Set-Cookie` response headers via `proxy_pass`, so no config change is required. The implementation plan includes a checklist step to verify with `curl -v` that:

- `Set-Cookie` from `/api/auth/login` reaches the browser unmodified (correct flags).
- `Cookie` headers reach the backend on subsequent requests.

### Logging contract

New audit actions follow the existing `<entity>.<verb>` pattern and re-use the `audit_log` columns; no schema change needed in the observability contract (`~/repos/configs/docs/observability-logging-contract.md`).

### GlitchTip

The frontend wrapper in `lib/api.ts` is rewritten; `ApiError` reporting must continue to attach the user identifier from `meQuery.data`, not a no-longer-existing `localStorage` token. The plan includes a verification step against the GlitchTip frontend agent guide.

### Dev environment

Running locally requires `COOKIE_SECURE=false` in the dev API env (Vite → FastAPI is plain HTTP). This is documented in `AGENTS.md` "Dev setup". Tests run in `TestClient` and bypass `Secure` because they use the ASGI transport directly.

## Threat model summary

| Threat | Mitigation |
|---|---|
| XSS exfiltrates session token | Both cookies are `httpOnly` — JS cannot read them. XSS can still abuse the session in-tab while it is open, but cannot replay outside the victim's browser. |
| CSRF on a mutating endpoint | `SameSite=Strict` cookies do not leave the SPA; custom `X-Portal-Client` header check on every mutating endpoint blocks any cross-origin POST, even from a hostile subdomain. |
| Stolen refresh replay | Rotation invalidates the previous refresh on every use. Reuse of a revoked refresh outside the 30-s grace burns the entire family and emits `auth.refresh.reuse_detected`. |
| Multi-tab / multi-device benign race | 30-s server-side grace returns the current family token instead of treating concurrent refresh as theft. |
| DB dump | Refresh tokens stored as `SHA-256(secret)`; raw values not recoverable from a dump. JWT secret is operational config, not in DB. |
| Long-lived JWT after compromise | JWT lives 10 minutes. There is no per-`jti` blocklist (acceptable given 10-min ceiling); a forced global revoke is done by rotating `JWT_SECRET`. |

## Risks and open items

- **No rate-limit on `/auth/login` or `/auth/refresh` yet.** A determined attacker with valid refresh material can hammer `/refresh`; without a limit, audit volume can spike. Tracked as a separate backlog item; the design here is rate-limit-friendly (one row per refresh, easy to bucket by `family_id` or `ip`).
- **`isAdmin` async-on-first-paint requires auditing all consumers.** Risk that an admin-gated component briefly renders the non-admin variant before `/auth/me` resolves. Mitigated by `isLoading` checks in `AuthGate` and skeleton states; the plan must enumerate every consumer.
- **Migration window for existing tokens.** During the rolling deploy, an in-flight request from a tab that loaded the old SPA may attempt `Authorization: Bearer …` against the new backend. New backend ignores `Authorization` entirely, so the request will 401, the SPA reload picks up the new code, and the user re-logs once. Acceptable for a household tool; documented in the plan's deploy note.
- **`ua-parser-js` dependency.** Sessions screen formatting depends on whether the dependency is already pulled in by another part of the SPA. The plan checks first and decides between using it and raw strings — does not add a new top-level dependency just for this.

## Testing plan (high-level)

### Backend

- Unit: token issuance, hashing, expiration math.
- Integration (`TestClient`):
  - `login → /me → access expires (monkeypatch clock) → /refresh → /me` happy path with cookies.
  - Reuse detection: capture refresh, rotate, present old refresh after 30 s → 401 + family revoked + audit event written.
  - Grace window: capture refresh, rotate, present old refresh inside 30 s → 200 with current family token.
  - Per-session logout revokes only the current family; other family still works.
  - `logout-all` revokes every family; subsequent `/refresh` from any returns 401.
  - `GET /sessions` returns one entry per family with `is_current` set correctly.
  - `DELETE /sessions/{family_id}` rejects 403 when family belongs to another user.
  - CSRF middleware: POST to `/api/admin/...` without `X-Portal-Client` → 403.
  - Alembic migration `0006` round-trips `up`/`down`.

### Frontend

- `api()` wrapper retries once on `access_expired` and surfaces other 401 codes unchanged.
- `refreshAccessToken` deduplicates concurrent callers (one network call for N waiters).
- `AuthContext` exposes `isLoading=true` until `/me` resolves, and `isAuthenticated=false` on 401.
- `AuthGate` shows a spinner during loading, not the unauthenticated view.
- Sessions screen renders the list, revokes a session, and triggers `logout-all`.
- Visual regression for `/settings/sessions` per project standard.
