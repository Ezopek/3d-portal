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

## Auth boundary scope

This design covers *app-level* authentication, but the portal sits behind nginx Basic auth on production (`infra/nginx-180/3d-portal.conf`). The two layers split responsibility as follows.

| Surface | App auth | Perimeter auth | Notes |
|---|---|---|---|
| `/api/admin/*` | required (access cookie) | required | All admin reads + writes. |
| `POST /api/auth/login` | not required | required | Entry point — verifies password directly. |
| `POST /api/auth/refresh` | not required (uses **refresh** cookie, not access) | required | Decodes refresh cookie via the rotation algorithm; access cookie is irrelevant here. |
| `POST /api/auth/logout` | tolerant — no cookie ⇒ 204 + clear | required | Idempotent; never errors so users can always leave. |
| `POST /api/auth/logout-all`, `POST /api/auth/logout-others` | required (access cookie) | required | Need to identify the user. |
| `GET /api/auth/me` | required (access cookie) | required | Returns the role/identity used by the SPA. |
| `GET /api/auth/sessions`, `DELETE /api/auth/sessions/{family_id}` | required (access cookie) | required | Per-family management. |
| SoT writes (model/file/tag/category mutations) | required (access cookie) | required | Live in `/api/admin/*` already. |
| SoT reads — `/api/categories`, `/api/tags`, `/api/models`, `/api/models/{id}`, `/api/models/{id}/files`, `/api/models/{id}/files/{file_id}/content` | **NOT required** | required | Anonymous at the app layer; only nginx Basic auth gates them. Verified: `apps/api/app/modules/sot/router.py` does not import `current_user`/`current_admin`. |
| `/api/share/*` and `/share/*` | not required | **NOT required** | Anonymous by design — share-link tokens authorize access; nginx exempts these paths from Basic auth. |

This is a deliberate, documented choice: catalog reads and file-content downloads stay perimeter-protected by nginx so that `<img src="/api/models/.../content">` and direct browser access still work without per-request app-auth headaches. **Consequence:** if the household ever exposes the portal beyond Basic auth (e.g. opens it on the public internet without nginx in front, or lets non-household users in), catalog reads become public until app-auth is added to the SoT read router. That migration is out of scope here but is a known follow-up; if it ships, the share file-content path needs signed URLs because share links must remain anonymous-by-design.

## Architecture

### Cookie design

| Cookie | Type | TTL | `Path` | `SameSite` | `Secure` | `httpOnly` | Contents |
|---|---|---|---|---|---|---|---|
| `portal_access` | JWT (HS256) | 10 min | `/api` | `Strict` | env-conditional | yes | `sub`, `role`, `iat`, `exp`, `jti` |
| `portal_refresh` | opaque random 256-bit (`secrets.token_urlsafe(32)`) | 30 days sliding | `/api/auth` | `Strict` | env-conditional | yes | reference into `refresh_tokens` table |

Three explicit choices:

1. **Path scoping (defense in depth, not authorization).** `portal_refresh` is scoped to `/api/auth` so it never leaves the auth surface — proxies, traces, and error reports outside `/api/auth/*` cannot leak it. `portal_access` is scoped to `/api`, so it is not sent to the `/share/*` static surface. Note: `portal_access` *is* sent to `/api/share/*` (still under `/api`), which is fine because share endpoints ignore session state and authorize via share-link tokens. Path scoping reduces accidental exposure; it is not an authorization boundary on its own.
2. **Refresh is opaque, not a JWT.** Refresh tokens must hit the DB anyway (rotation, revoke, family detection). Making them JWTs adds key management and a redundant `exp` without benefit. We store `SHA-256(secret)`, never the raw value — a DB dump cannot be replayed.
3. **Access is a JWT.** Required for the auth dependency to validate per request without a DB hit. There is no per-`jti` blocklist — `JWT_SECRET` rotation is the only global "revoke now" lever, and that is acceptable given the 10-min ceiling.

### `Secure` flag in dev and the HTTPS-only consequence

`Secure` cookies are not transmitted over plain HTTP, which breaks the local browser-to-Vite flow (the SPA lives at `http://localhost:5173`, Vite proxies `/api` to FastAPI on `http://localhost:8000`). Resolution:

- New setting `cookie_secure: bool = True` in `app/core/config.py`.
- Local dev `.env` sets `COOKIE_SECURE=false`. Production `.env` keeps the default.
- `set_cookie(...)` calls pass `secure=settings.cookie_secure`.
- `SameSite=Strict` works in both: dev is same-site between Vite (`localhost:5173`) and FastAPI on `localhost` — Vite proxies `/api → http://localhost:8000` per `apps/web/vite.config.ts`, so the browser sees a single origin (`localhost:5173`). Prod is same-site under `3d.ezop.ddns.net`.

**Operational consequence:** the production `docker-compose.yml` exposes the web container (nginx serving the SPA + proxying `/api/*` to the API container) on host port `8090` for direct LAN access. The API container itself is not directly exposed; clients always reach the API through the web/nginx proxy. After this change, **interactive browser sessions over `http://192.168.2.190:8090` no longer work** — `Secure` cookies are dropped on plain HTTP regardless of which container terminates the connection. The port stays useful for `curl` against the API path and for integration tests that do not need browser-set cookies. Documented in `AGENTS.md` "Operational notes". User-facing access is `https://3d.ezop.ddns.net` only.

`TestClient` (`fastapi.testclient`, ASGI transport) bypasses the `Secure` flag because it does not enforce HTTP-vs-HTTPS — tests can run with `cookie_secure=true` without setup, but the test fixture sets `COOKIE_SECURE=false` to keep behavior aligned with explicit env state.

### Database schema

New table created via Alembic migration `0009_refresh_tokens` (head is `0008_drop_legacy_tables`). The production DB is SQLite (`infra/docker-compose.yml` mounts `sqlite:////data/state/portal.db`), so column types follow the project pattern from migration `0005`: `sa.Uuid(as_uuid=True)`, `sa.DateTime()`, `sa.String()`. UUIDs are generated in Python (`uuid.uuid4()`) at insert time — there is no server-side default.

```
refresh_tokens
  id                 UUID (sa.Uuid)        PK, generated in Python
  user_id            UUID (sa.Uuid)        NOT NULL, FK → user.id, ON DELETE CASCADE
  family_id          UUID (sa.Uuid)        NOT NULL  -- shared across the rotation chain
  family_issued_at   DateTime              NOT NULL  -- timestamp of the family's first token; copied to descendants
  token_hash         String                NOT NULL, UNIQUE  -- hex(SHA-256(secret))
  issued_at          DateTime              NOT NULL, set in Python at insert
  expires_at         DateTime              NOT NULL  -- issued_at + 30d
  replaced_at        DateTime              NULL      -- when this token was rotated
  replaced_by_id     UUID (sa.Uuid)        NULL, FK → refresh_tokens.id
  revoked_at         DateTime              NULL
  revoke_reason      String                NULL  -- enforced via CHECK constraint
  last_used_at       DateTime              NULL      -- bumped each refresh
  ip                 String                NULL      -- IP as text (SQLite has no INET)
  user_agent         String                NULL      -- truncated to 500 chars in app code

CHECK CONSTRAINT  revoke_reason IS NULL OR revoke_reason IN
                    ('rotated','logout','logout_all','reuse_detected','manual')
INDEX ix_refresh_tokens_user_active     ON (user_id) WHERE revoked_at IS NULL
INDEX ix_refresh_tokens_family          ON (family_id)
UNIQUE INDEX ux_refresh_tokens_family_active
                                        ON (family_id) WHERE revoked_at IS NULL
```

The partial UNIQUE index `ux_refresh_tokens_family_active` is the schema-level invariant that prevents two concurrent refreshes from both succeeding — only one row per family can have `revoked_at IS NULL` at any moment. Combined with SQLite's WAL + `PRAGMA busy_timeout=5000` (already configured in `apps/api/app/core/db/session.py`), concurrent refreshes serialize cleanly: the second writer either waits for the first or hits the unique constraint and retries.

SQLite supports both partial indexes and `CHECK` constraints, so the migration is portable to PostgreSQL later (when/if we move) without changing column types — only `String` → `INET` for `ip` would be worth tightening.

`family_issued_at` exists so a future absolute-session-lifetime cap (e.g. force re-login after 180 days regardless of activity) can be applied with a single comparison. **This design does not enforce an absolute cap; sliding-only is a conscious deviation from OWASP "absolute session timeout" guidance**, justified by the household scope (no privileged operations, low blast radius). Adding `family_issued_at` now keeps the option open without a follow-up migration.

Cleanup: a daily worker job `cleanup_refresh_tokens` (arq scheduled task) deletes rows where
`(revoked_at IS NOT NULL AND revoked_at < now - 7 days) OR (expires_at < now - 7 days)`. Audit-log lifecycle events live separately in `audit_log` and are not affected by this cleanup.

### Refresh rotation algorithm

`POST /api/auth/refresh` reads `portal_refresh` cookie and:

1. If cookie absent → 401 `{"detail": "no_refresh"}`.
2. Look up by `token_hash = sha256(secret)`. If not found → 401 `{"detail": "invalid_refresh"}`.
3. If `expires_at < now()` → 401 `{"detail": "refresh_expired"}`.
4. If `revoked_at IS NOT NULL`:
   - If `revoke_reason = 'rotated'` AND `now() - replaced_at < 30 s` AND `request.user_agent == active_descendant.user_agent`:
     - **Grace path.** Look up the active descendant in the family (the row where `revoked_at IS NULL`; the partial UNIQUE index guarantees there is at most one). Reissue cookies bound to that descendant; do not rotate again. The UA match is a cheap fingerprint that blocks cross-device replay during grace — a benign multi-tab race within the same browser shares the same UA, so the legit case still works.
     - If UA does not match → log the anomaly (structured warning event with `family_id`, presented `user_agent`, descendant's `user_agent`) but **do not** burn the family yet — return 401 `{"detail": "force_relogin"}`. The legitimate user still has the active token; an attacker without UA match is denied.
     - If no active descendant exists (first rotation already revoked again, e.g. logout) → 401 `{"detail": "force_relogin"}`.
   - Else:
     - **Reuse detected.** Update all rows in the family to `revoked_at = now(), revoke_reason = 'reuse_detected'`. Emit `auth.refresh.reuse_detected` audit event with `user_id`, `family_id`, `ip`, `user_agent`. Return 401 `{"detail": "force_relogin"}`.
5. Happy path (statement order **matters** because of `ux_refresh_tokens_family_active`):
   - Generate `new_secret = secrets.token_urlsafe(32)`.
   - **Step 1 — UPDATE old row:** `revoked_at = now(), revoke_reason = 'rotated', replaced_at = now()`. Do **not** touch `replaced_by_id` yet (the new row does not exist, and the FK would fail with SQLite's default immediate FK checking). After this step the family has zero active rows, so the next INSERT will not collide with the partial UNIQUE index.
   - **Step 2 — INSERT new row:** same `family_id`, same `family_issued_at` (copied from the old row), `token_hash = sha256(new_secret)`, `issued_at = now()`, `expires_at = now() + 30 d`, `last_used_at = now()`, `ip`, `user_agent`.
   - **Step 3 — UPDATE old row again:** `replaced_by_id = new.id`. The new row now exists, so the FK is satisfied.
   - **Step 4 — Issue new access JWT** (`exp = now + 10 m`).
   - Set both cookies. Emit `auth.refresh.success` structured log. Return `200 {"user": MeResponse}`.

   The two-step UPDATE on the old row is the explicit cost of enforcing the partial-active-family invariant in the schema. It is one extra round-trip per rotation (10/h per active user worst case) — negligible vs. the correctness it buys.

**Concurrency.** All read+update steps run inside a single transaction. We rely on three layers, in this order:

1. The partial UNIQUE index `ux_refresh_tokens_family_active` makes "two active rows per family" representable only as an `IntegrityError`. The second refresh's `INSERT` either waits or fails — the schema is the source of truth.
2. SQLite WAL + `PRAGMA busy_timeout = 5000` (already configured in `apps/api/app/core/db/session.py`) serializes writers globally. Under contention the second transaction blocks for up to 5 s rather than failing immediately.
3. The handler catches `IntegrityError` on the new-row INSERT, rolls back, re-reads the candidate row, and re-runs the algorithm. The re-read sees the first writer's revocation and falls into the grace branch (correct outcome).

This avoids per-engine `isolation_level` tweaks (SQLAlchemy's SQLite dialect does not accept `"IMMEDIATE"` as an engine isolation level — only `READ UNCOMMITTED`, `SERIALIZABLE`, `AUTOCOMMIT`). No explicit row locks are needed at this scale.

### Endpoints

| Method + path | Status | Description |
|---|---|---|
| `POST /api/auth/login` | changed | Verifies password. Creates a new family with one fresh refresh row. Sets both cookies. Returns `{user: MeResponse}`. No tokens in body. |
| `POST /api/auth/refresh` | new | Algorithm above. |
| `POST /api/auth/logout` | changed | Revokes current refresh's family with `reason='logout'`. Clears both cookies (`Max-Age=0`). 204. |
| `POST /api/auth/logout-all` | new | Revokes **every** family for the user (including the current one) with `reason='logout_all'`. Clears both cookies on the calling response. 204. UI: "Logout everywhere". |
| `POST /api/auth/logout-others` | new | Revokes every family for the user **except** the calling family with `reason='logout_all'`. Does **not** clear cookies — the calling session continues. 204. UI: "Logout from all other devices" — used by the sessions screen. |
| `GET /api/auth/me` | changed | Reads access from cookie. Same response shape as today. |
| `GET /api/auth/sessions` | new | Returns `[{family_id, last_used_at, ip, user_agent, is_current}]` — one entry per family (not per token in the chain). |
| `DELETE /api/auth/sessions/{family_id}` | new | Revokes the named family with `reason='manual'`. 403 if the family does not belong to the calling user. If the family is the current one, the response also clears cookies. |

Granularity choice: sessions UI is per-family because users think "the tablet in the living room", not per-token in the rotation chain.

**Edge cases (idempotent UX).** Logout-style endpoints must succeed even when the server-side state is partially gone — users should never see an error while trying to leave.

| Situation | Behavior |
|---|---|
| `POST /auth/logout` with valid access cookie but no refresh cookie | 204; clear `portal_access` cookie. No DB write. |
| `POST /auth/logout` after another tab already revoked the family | 204; clear both cookies; do not write a second `auth.logout` audit event (idempotent). |
| `POST /auth/logout` with no auth at all | 204; clear cookies. The endpoint exempts itself from the auth dependency. |
| `POST /auth/logout-others` when no other families exist | 204; no DB write; `revoked_count=0`. Calling session unchanged. |
| `POST /auth/logout-others` when calling refresh cookie does not match any family | 401 — caller is anonymous; sessions screen would not have rendered the button. |
| `GET /auth/sessions` when current refresh cookie is absent or stale | 200 with the list, but `is_current` is `false` for every entry. UI shows "Logout everywhere" button only (no "logout from others" target). |
| `DELETE /auth/sessions/{family_id}` revoking the current family | 204 + clear both cookies + structured log; client treats as logout (redirect to `/login`). |
| `DELETE /auth/sessions/{family_id}` for an already-revoked family | 204 (idempotent); no second audit event. |
| `DELETE /auth/sessions/{family_id}` for a family that is not the user's | 403 (per spec), regardless of revoke state. |

`POST /auth/logout-all` is exempt from the CSRF middleware's "must have access cookie" precondition: a stale tab calling `logout-all` should still complete the cleanup. The endpoint does require a valid access cookie to identify the user, but is tolerant of missing refresh cookie.

### Auth dependency rewrite (`app/core/auth/dependencies.py`)

`HTTPBearer` is removed. The dependency reads `request.cookies.get("portal_access")` and decodes the JWT. Error bodies use stable `detail` codes the client can branch on:

| Condition | Status | `detail` |
|---|---|---|
| No cookie | 401 | `missing_access` |
| JWT expired | 401 | `access_expired` |
| JWT invalid signature / malformed | 401 | `invalid_access` |
| Role not in allowed set | 403 | `forbidden_role` |
| Admin required and role ≠ admin | 403 | `admin_required` |

**Client refresh trigger.** The client triggers reactive refresh on **both** `access_expired` AND `missing_access`. The cookie's `Max-Age` matches the JWT TTL (10 min), so after the cookie expires browser-side, the next request arrives with no `portal_access` cookie at all — the server returns `missing_access`, not `access_expired`. Refreshing on both codes covers "JWT expired but cookie still on the wire" and "cookie was dropped by the browser" identically.

The client must guard against infinite retry: each request is allowed at most one refresh attempt, and if `/auth/refresh` itself returns 401 (any code), the client treats the user as anonymous and stops retrying. The other 401 codes (`invalid_access`, `forbidden_role`, `admin_required`) mean force-relogin without an attempted refresh.

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
- `/api/share/*` is exempt because share endpoints are anonymous and authorize via share-link tokens; even though a logged-in browser does send `portal_access` to `/api/share/*` (path scoping is `/api`, not `/api/admin`), the endpoints do not consult the session cookie.
- `/api/auth/login` and `/api/auth/refresh` are NOT exempt — login-CSRF (session fixation) and refresh-CSRF are real attacks. The SPA fetch wrapper sets the header on every call, so this is invisible to clients.

**Standing assumption (CORS).** The custom-header CSRF defense relies on no cross-origin browser being able to set `X-Portal-Client` on a credentialed request without triggering a CORS preflight that we deliberately do not respond to. The FastAPI app **does not** install `CORSMiddleware` today and must not start permitting cross-origin credentialed requests without revisiting this CSRF model. Adding CORS for any non-same-origin caller would weaken this defense and require a token-based CSRF (double-submit-cookie) instead.

**Direct-fetch callsites — must be migrated.** Two callsites bypass the `api()` wrapper and need to be updated to pass `X-Portal-Client: web` and follow the credentials/refresh contract:

- `apps/web/src/modules/catalog/hooks/mutations/useUploadFile.ts` — multipart upload to `/api/admin/models/{id}/files`. After this change, missing the header → CSRF middleware returns 403. Refactor: keep direct `fetch` (so the multipart `FormData` body is not double-handled), but add `headers: {"X-Portal-Client": "web"}`, `credentials: "include"`, and reuse `refreshAccessToken()` on a 401 with `access_expired`/`missing_access`. `FormData` is a snapshot, so retry with the same instance is safe.
- `apps/web/src/modules/catalog/components/viewer3d/hooks/useStlGeometry.ts` — fetches STL file content. STL endpoints stay perimeter-protected (anonymous at app layer), so this does not need `X-Portal-Client` for CSRF reasons (it is a `GET`), but it does need to be aware that adding `credentials: "include"` is unnecessary and may even be undesirable here. Decision: leave this fetch untouched. Documented to confirm we audited it.

A grep audit (`grep -rn "fetch(" apps/web/src --include="*.ts" --include="*.tsx" | grep -v "lib/api.ts" | grep -v "\.test\."`) is part of the implementation plan to confirm no third callsite slips in.

**Defense in depth (deferred).** `Origin` and `Sec-Fetch-Site` header checks are a recognized additional layer. Not implemented in this slice — the SameSite-Strict + custom-header combination is sufficient for the current threat model. If we ever loosen CORS or expose the portal beyond Basic auth, revisit this.

### Audit events vs structured logs

Active users with a 10-minute access TTL emit many `auth.refresh.success` events per day. Persisting every one to `audit_log` (which is intentionally not garbage-collected) is poor signal-to-noise. Split:

**Persistent `audit_log` rows (incidents + lifecycle):**

| Action | Emitted by | Notes |
|---|---|---|
| `auth.login.success` | existing | unchanged |
| `auth.login.fail` | existing | unchanged |
| `auth.refresh.reuse_detected` | new | `actor_user_id=user`, `after={family_id, ip, user_agent}` — security incident, must persist |
| `auth.logout` | changed | `actor_user_id`, `after={family_id}` |
| `auth.logout_all` | new | `actor_user_id`, `after={scope: "all" \| "others", revoked_count}` — same action string for both `logout-all` and `logout-others`; the `scope` field disambiguates. |
| `auth.session.revoked` | new | manual revoke from `/settings/sessions`; `after={family_id}` |

**Structured logs only (high-volume, hot-path):**

| Action | Notes |
|---|---|
| `auth.refresh.success` | `user_id`, `family_id`, `ip`, `user_agent` — emitted via `app.core.logging` to the OTLP/Glitchtip pipeline; not in `audit_log`. |
| `auth.refresh.grace_ua_mismatch` | new structured warning when grace branch denies a refresh because of UA mismatch (see algorithm step 4). Useful signal without spamming `audit_log`. |

If we later need rate analysis on successful refreshes, the structured log pipeline already feeds Loki/Glitchtip — querying there is cheaper than scanning `audit_log`.

### Frontend changes

#### `apps/web/src/lib/api.ts` (rewrite)

- `authenticated` parameter removed. Every call sends cookies; auth is server-decided. ~30 callsites simplify (token-marker boilerplate disappears).
- `credentials: "include"` set on every fetch.
- Header `X-Portal-Client: web` always set.
- Reactive refresh on `access_expired` OR `missing_access`, with one-shot retry guard:

```ts
let response = await doFetch();
if (response.status === 401) {
  const body = await response.clone().json().catch(() => ({}));
  const detail = body?.detail;
  if ((detail === "access_expired" || detail === "missing_access") && !init._didRefresh) {
    const ok = await refreshAccessToken();   // singleton, see below
    if (ok) {
      // Mark the retry so a second 401 cannot loop us back into refresh.
      response = await doFetch({ ...init, _didRefresh: true } as RequestInit);
    }
  }
}
```

The `_didRefresh` marker (or equivalent local flag) caps each request at one refresh attempt — if `/auth/refresh` succeeded but the retried call still 401s, we surface the error to the caller rather than loop. If `/auth/refresh` itself returns 401, `refreshAccessToken()` resolves `false` and we surface the original 401.

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

Consequence: `isAdmin` is asynchronous on first paint. The implementation plan must treat the following as in-scope, not incidental cleanup:

- **`AuthGate.tsx`** — must check `isLoading` *before* `isAuthenticated`. Render an app-shell skeleton/spinner while loading; never render the unauthenticated/login view based on a transient "no role yet" state.
- **All `isAdmin` consumers** — every component that branches on `isAdmin` (admin tabs, edit affordances, the audit-log Activity tab) must render a skeleton or nothing while `isLoading=true`, not the non-admin variant. Plan enumerates the consumers via grep.
- **`UserMenu.tsx`** — display the real `display_name` / `email` from `meQuery.data` instead of any hardcoded role label. The current shell shows the role generically; after this change it should show the actual user.
- **Session-expired UX** — when `meQuery` returns 401 (or any reason the user becomes anonymous), redirect to `/login?next=<current-path>` so re-login lands the user back where they were instead of on the dashboard. Login route reads `?next` and navigates after success.

#### Sessions screen (`/settings/sessions`)

- Lazy-loaded route. Link from `UserMenu.tsx` next to "Logout".
- Hooks: `useSessions()` (`GET /auth/sessions`), `useRevokeSession(family_id)` (`DELETE /auth/sessions/{id}`), `useLogoutOthers()` (`POST /auth/logout-others`, used by the "Logout from all other devices" button — keeps current session), `useLogoutAll()` (`POST /auth/logout-all`, used by the global "Logout everywhere" affordance in `UserMenu`).
- Layout: a table with `Last used` (relative time, with absolute timestamp as `title` tooltip), `Device` (parsed user-agent — use existing `ua-parser-js` if already a dep, otherwise raw string truncated to 50 chars; the implementation plan resolves this), `IP`, `is_current` badge, `Revoke` button. Above the table: `Logout from all other devices` button (disabled when there is no "other").
- **Mobile layout** — at `<sm` breakpoint the table collapses into stacked cards (one per session) so the action button stays reachable on a phone; matches existing mobile-first patterns elsewhere in the SPA.
- **Current-session protection** — the `Revoke` action on the row marked `is_current` shows a confirmation dialog ("This will log you out of this device — continue?") before firing. Other rows revoke immediately with a small toast.
- **Empty / unknown values** — when `ip` or `user_agent` is null (older row, or not yet captured), render `Unknown device` / `Unknown IP` placeholders with appropriate localized strings.
- **i18n** — all sessions-screen strings live in `apps/web/src/locales/en.json` and `apps/web/src/locales/pl.json`. No raw English strings in the component.
- Revoking the current session redirects to `/login` (preserving `?next` if applicable). Revoking another session refetches the list.
- Visual regression test for the screen (Playwright) per project standard for UI changes — desktop and mobile viewports.

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
| Stolen refresh replay | Rotation invalidates the previous refresh on every use. Reuse of a revoked refresh outside the 30-s grace burns the entire family and emits `auth.refresh.reuse_detected`. Inside the grace window, UA-mismatch denies the replay without burning the family (legitimate user keeps working). |
| Multi-tab / multi-device benign race | 30-s server-side grace + matching `user_agent` returns the current family token instead of treating concurrent refresh as theft. |
| Stolen refresh used inside grace by same UA | **Conscious tradeoff (honestly described):** an attacker who (a) has stolen the previous-generation refresh secret AND (b) presents it within the 30-s grace window AND (c) matches the legitimate descendant's `User-Agent` will obtain the current active token. From that point the attacker holds a valid session and can keep rotating it indefinitely. Detection happens **only when the legitimate browser next presents *its* now-stale refresh** — at which point the family is burned. If the legitimate user closes the tab, lets the device sleep, or simply does not return for hours/days, the attacker's session persists for that entire window. The bound is "until the legitimate client refreshes again", not "≤10 min" — that earlier framing was wrong. |
| Mitigations available if this tradeoff is unacceptable | (a) drop the server-side grace and rely on the client-side `BroadcastChannel` cross-tab pattern instead — same multi-tab UX, no server-side window for replay; (b) pin grace branch to a short window like 5 s and accept occasional tab relogin; (c) tie grace to refresh-cookie-bound IP bucket as additional fingerprint. None implemented in this slice — the current design accepts the tradeoff for its UX simplicity. The schema and frontend retain the option to switch to (a) later without migration: remove the grace branch in the algorithm, add `BroadcastChannel("portal-auth")` to the singleton, and roll forward. |
| DB dump | Refresh tokens stored as `SHA-256(secret)`; raw values not recoverable from a dump. JWT secret is operational config, not in DB. |
| Long-lived JWT after compromise | JWT lives 10 minutes. There is no per-`jti` blocklist (acceptable given 10-min ceiling); a forced global revoke is done by rotating `JWT_SECRET`. |

## Risks and open items

- **No rate-limit on `/auth/login` or `/auth/refresh` in this slice.** Concrete follow-up (named, not anonymous backlog): integrate `slowapi` (FastAPI-native, Redis-backed). Buckets:
  - `/auth/login` — 10 attempts per 15 minutes per IP, then 429.
  - `/auth/refresh` — 60 attempts per minute per `family_id` (so a runaway client cannot hammer); 200/min per IP as outer bound.
  The current schema already captures `ip`, `user_agent`, `family_id` so the rate-limit slice does not require migration. Tracked as the next slice after this auth flow ships.
- **Grace-window UA-mismatch policy is "deny but don't burn".** Implementation must emit `auth.refresh.grace_ua_mismatch` structured log so the household can spot real attacks; the plan includes a Glitchtip alert step.
- **`isAdmin` async-on-first-paint requires auditing all consumers.** Risk that an admin-gated component briefly renders the non-admin variant before `/auth/me` resolves. Mitigated by `isLoading` checks in `AuthGate` and skeleton states; the plan enumerates every consumer (grep of `isAdmin`, `isAdminOrAgent`).
- **Migration window for existing tokens.** During the rolling deploy, an in-flight request from a tab that loaded the old SPA may attempt `Authorization: Bearer …` against the new backend. New backend ignores `Authorization` entirely, so the request will 401, the SPA reload picks up the new code, and the user re-logs once. Acceptable for a household tool; documented in the plan's deploy note.
- **`ua-parser-js` dependency.** Sessions screen formatting depends on whether the dependency is already pulled in by another part of the SPA. The plan checks first and decides between using it and raw strings — does not add a new top-level dependency just for this.
- **Indefinite active sessions.** No absolute session lifetime cap (sliding only). Conscious deviation from OWASP guidance, justified by the household scope. The schema captures `family_issued_at`, so adding an absolute cap later is a config change plus a `WHERE` clause, no migration.

## Testing plan (high-level)

### Backend

- Unit: token issuance, hashing, expiration math.
- Integration (`TestClient`):
  - `login → /me → access expires (monkeypatch clock) → /refresh → /me` happy path with cookies.
  - Reuse detection: capture refresh, rotate, present old refresh after 30 s → 401 + family revoked + audit event written.
  - Grace window: capture refresh, rotate, present old refresh inside 30 s → 200 with current family token.
  - Per-session logout revokes only the current family; other family still works.
  - `logout-all` revokes every family; subsequent `/refresh` from any returns 401.
  - `logout-others` revokes every family except the calling family; calling session's next `/refresh` still succeeds; revoked families' refresh attempts return 401.
  - `GET /sessions` returns one entry per family with `is_current` set correctly.
  - `DELETE /sessions/{family_id}` rejects 403 when family belongs to another user.
  - CSRF middleware: POST to `/api/admin/...` without `X-Portal-Client` → 403.
  - Concurrent refresh: two parallel `/auth/refresh` calls with the same refresh cookie — one wins (rotates), the other lands in grace and returns the new active token (assuming UA matches in the test).
  - Grace UA-mismatch: present rotated refresh during grace from a different `User-Agent` → 401 + `auth.refresh.grace_ua_mismatch` structured log + family **not** burned.
  - Logout idempotency: `POST /auth/logout` without refresh cookie → 204; double-logout from two tabs → both succeed, single audit row.
  - Edge-case `GET /auth/sessions` with stale refresh cookie → list returned, every entry has `is_current=false`.
  - Alembic migration `0009` round-trips `up`/`down`.

### Frontend

- `api()` wrapper retries once on `access_expired` AND `missing_access`; surfaces other 401 codes unchanged. Second 401 after refresh does not loop.
- `refreshAccessToken` deduplicates concurrent callers (one network call for N waiters).
- `AuthContext` exposes `isLoading=true` until `/me` resolves, and `isAuthenticated=false` on 401.
- `AuthGate` shows a spinner during loading, not the unauthenticated view.
- `UserMenu` displays `display_name` from `meQuery.data`, not a hardcoded role label.
- Session-expired flow preserves `?next=` and routes back to the original page after re-login.
- `useUploadFile.ts` migrated: includes `X-Portal-Client`, `credentials: include`, retries multipart upload once on `access_expired`/`missing_access` reusing the same `FormData`.
- Sessions screen renders the list (desktop + mobile), revokes a session (with current-session confirmation), triggers `logout-all`, and translates strings via `apps/web/src/locales/{en,pl}.json`.
- Visual regression for `/settings/sessions` per project standard — desktop (1280) and mobile (375) viewports.
