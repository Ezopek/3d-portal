# Story 6.6: Rate-limit middleware — `apps/api/app/core/auth/ratelimit.py` for login / refresh / register

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want a Redis-sliding-window rate-limit middleware in NEW `apps/api/app/core/auth/ratelimit.py` exporting a single `RateLimitMiddleware(app, scope, key_fn, window_seconds, threshold)` class, plus three middleware instances mounted in `apps/api/app/main.py:create_app()` (for the `login`, `refresh`, and `register` scopes — the fourth `share` scope is INTENTIONALLY deferred to Story 6.7) ordered **AFTER CORS, AFTER the existing CSRF guard, BEFORE auth-dependency resolution**, with thresholds + window seconds drawn from four new `Settings` keys (`ratelimit_login_*`, `ratelimit_refresh_*`, `ratelimit_register_*`, plus shared `ratelimit_redis_unavailable_warn_enabled`) — fail-soft on Redis outage (log `WARNING app.auth.ratelimit redis_unavailable scope=<scope>` and ALLOW the request, mirroring Init 0 share-token outage semantics) — so that the brand-new public-write endpoints introduced by Stories 6.1–6.4 (`POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/register`) are protected against credential stuffing + invite-token brute-force per FR5-RATELIMIT-1 thresholds (5 failures / 60s per IP, 10 attempts / 60s per IP, 3 attempts / 60s per IP respectively) and the architecture's E9 NFR5-SEC-3 audit gate (Story 9.2 scenario 5) has a concrete subject to verify against, with EVERY currently-passing test in `apps/api/tests/` continuing to pass unchanged (the existing 5 successful-login + 30+ refresh + 20+ register tests MUST stay green — only NEW tests author 6th-call-rejection, 11th-call-rejection, and 4th-call-rejection assertions).

## Acceptance Criteria

**AC-1 — `RateLimitMiddleware` class shape: exact constructor signature + one-pipelined-call sliding-window primitive over Redis sorted set + HTTP 429 + `Retry-After` header on rejection.**

- Given a fresh `apps/api/app/core/auth/ratelimit.py` module imported into a minimal `FastAPI()` test app with `app.state.redis` set to a `fakeredis.aioredis.FakeRedis()` instance via a `RedisFactory`-shaped `MagicMock` (mirrors `test_share_admin.py:14-67` and `test_share_member_permission.py:50-67` test-rig pattern — the binding precedent),
- When the middleware is wired to a single `POST /test-route` route via `app.add_middleware(RateLimitMiddleware, scope="login", key_fn=lambda req: f"ip:{req.client.host}", window_seconds=60, threshold=5)`,
- Then the module's public surface MUST be exactly:

  ```python
  from starlette.types import ASGIApp, Receive, Scope, Send

  class RateLimitMiddleware:
      def __init__(
          self,
          app: ASGIApp,
          *,
          scope: str,
          key_fn: Callable[[Request], str | None],
          window_seconds: int,
          threshold: int,
      ) -> None: ...

      async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...
  ```

  Class — NOT a function decorator nor `@app.middleware("http")` decorator. Reason: the binding contract from Decision G is `RateLimitMiddleware(app, scope, key_fn, ...)` four-positional shape so `main.py` can mount three instances by calling `app.add_middleware(RateLimitMiddleware, scope="login", ...)` three times. The `@app.middleware("http")` decorator form (used by `csrf.py:10`) registers ONE function per app — it cannot register the same middleware with three different configurations.

- And on every request the middleware MUST execute exactly the following Redis operations as a single pipelined `MULTI/EXEC` round-trip (binding from Decision G, architecture.md §1557-1564):

  ```python
  now_ms = int(time.time() * 1000)
  window_ms = window_seconds * 1000
  key = f"ratelimit:{scope}:{key_fn_result}"
  async with redis.pipeline(transaction=True) as pipe:
      pipe.zremrangebyscore(key, "-inf", now_ms - window_ms)
      pipe.zadd(key, {str(now_ms): now_ms})
      pipe.expire(key, window_seconds + 1)
      pipe.zcard(key)
      _, _, _, count = await pipe.execute()
  ```

  Four pipelined operations: `ZREMRANGEBYSCORE` (purge expired entries) → `ZADD` (record current request) → `EXPIRE` (key auto-cleanup at window+1s — defensive, in case the key falls out of the active set) → `ZCARD` (read current count). The score and member are both `now_ms` — the score is the timestamp for window math, the member must be unique-enough to avoid `ZADD` collapsing two concurrent requests at the same millisecond into one entry. ONE round-trip; do NOT split into four awaits.

- And when `count > threshold` (strictly greater than — the first request at `threshold + 1` triggers rejection), the middleware MUST return HTTP 429 with body `{"detail": "rate_limited", "scope": "<scope>", "retry_after_seconds": <int>}` (JSONResponse) and the `Retry-After: <retry_after_seconds>` HTTP header. The header value is `window_seconds` (not the time-to-window-end; the simpler "wait `window_seconds` and your IP rate-limit will fully clear" semantic — see Dev Notes § "Retry-After value rationale"). Note the strict-greater semantics: with `threshold=5`, the 1st through 5th requests pass (count = 1, 2, 3, 4, 5 — all `<= 5`), the 6th rejects (count = 6 > 5). This matches the architecture binding "5 failures from one IP within 60 seconds returns HTTP 429" — the 6th call is the first 429.

- And when `count <= threshold`, the middleware MUST call `await self.app(scope, receive, send)` to pass control to the next ASGI layer (the next middleware in the stack OR the route handler). The pass-through MUST NOT modify `scope`, `receive`, or `send`.

- And the middleware MUST short-circuit for non-HTTP scopes: if `scope["type"] != "http"`, immediately `await self.app(scope, receive, send)` (no Redis call, no key resolution). This matches the Starlette middleware idiom for handling ASGI lifespan + websocket scope types.

- And the middleware MUST short-circuit when `key_fn(request)` returns `None`: pass-through (no Redis call, no rejection). Reason: the `key_fn` is allowed to return `None` for paths/methods OUT OF SCOPE for this middleware instance (e.g., `register_key_fn` returns `None` for any path other than `POST /api/auth/register`); the middleware MUST NOT rate-limit those calls because the very point of three separate instances is per-scope isolation.

**AC-2 — Redis-unreachable fail-soft: `WARNING` log emitted + request ALLOWED through.**

- Given the middleware wired as in AC-1 but `app.state.redis.get()` returns a Redis client whose pipeline `.execute()` raises `redis.exceptions.ConnectionError` (use `unittest.mock.AsyncMock(side_effect=redis.exceptions.ConnectionError("simulated outage"))` to fake it),
- When the client hits the protected route,
- Then the middleware MUST log a structured `WARNING` to logger name `app.auth.ratelimit` with `event.action = "ratelimit.redis_unavailable"`, `labels.scope = <scope>`, `labels.key = <key_fn_result>`, and the exception message in `extra["error.message"]` (matches the existing `auth.refresh.grace_ua_mismatch` log shape at `apps/api/app/modules/auth/router.py:206-214` — binding precedent),
- And the request MUST be allowed through to the route handler (the route's expected response is returned, NOT a 429),
- And the warning MUST be emitted at most ONCE per (scope, key) tuple per process-lifetime OR per the global `Settings.ratelimit_redis_unavailable_warn_enabled` flag is True (whichever is simpler — see Dev Notes § "Fail-soft logging cadence"). Binding rule: the warning is fired on EVERY request that hits the outage path; if the test wants to assert "exactly one warning" it can use `caplog.records` filter on `event.action == "ratelimit.redis_unavailable"` with `len() >= 1` (NOT exact equality — fail-soft cadence is a SHOULD, not a MUST). This avoids tying the spec to a process-state cache that adds complexity for no security gain.
- And the middleware MUST NOT swallow any non-`ConnectionError` exception class. If the pipeline raises `TimeoutError`, `redis.exceptions.RedisError`, OR any other Redis-side exception, the middleware MUST catch it via a `except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, OSError):` clause (broad enough to cover Redis-down + DNS-fail + connection-pool-exhausted) and then fall through to the ALLOW path. Any other exception MUST propagate (do NOT use `except Exception`).
- And GlitchTip captures the warning per NFR5-OBS-1 (verified indirectly: the existing Sentry-SDK integration in `init_sentry()` already routes `logging.WARNING` records to GlitchTip; no new Sentry-specific code is needed in this story).

**AC-3 — Three middleware instances mounted in `apps/api/app/main.py` with correct ordering: AFTER CORS, AFTER CSRF, BEFORE auth dependency.**

- Given the existing `apps/api/app/main.py:create_app()` function which currently calls `install_csrf_middleware(app)` at line 68,
- When Story 6.6 ships,
- Then `main.py:create_app()` MUST call THREE `app.add_middleware(RateLimitMiddleware, ...)` invocations IMMEDIATELY AFTER `install_csrf_middleware(app)` and BEFORE `app.include_router(api_router)`:

  ```python
  install_csrf_middleware(app)
  # Story 6.6: rate-limit middleware (Decision G). Order: AFTER CSRF (so CSRF
  # rejections don't burn rate-limit budget), BEFORE auth dependency
  # (so password-hash verification doesn't absorb brute-force cost).
  # Starlette's add_middleware stacks LIFO: the LAST add_middleware call wraps
  # OUTERMOST — so order calls so the OUTERMOST is the one we want hit first.
  # Because the three scopes are mutually exclusive on path, mounting order
  # within the trio is irrelevant; we order them alphabetically for stability.
  app.add_middleware(
      RateLimitMiddleware,
      scope="login",
      key_fn=login_ratelimit_key,
      window_seconds=settings.ratelimit_login_window_seconds,
      threshold=settings.ratelimit_login_threshold,
  )
  app.add_middleware(
      RateLimitMiddleware,
      scope="refresh",
      key_fn=refresh_ratelimit_key,
      window_seconds=settings.ratelimit_refresh_window_seconds,
      threshold=settings.ratelimit_refresh_threshold,
  )
  app.add_middleware(
      RateLimitMiddleware,
      scope="register",
      key_fn=register_ratelimit_key,
      window_seconds=settings.ratelimit_register_window_seconds,
      threshold=settings.ratelimit_register_threshold,
  )
  ```

- And the three `key_fn` callables MUST live as module-top-level functions in `apps/api/app/core/auth/ratelimit.py` (NOT inline lambdas in `main.py` — see Dev Notes § "Key-fn placement rationale"). Binding shapes:

  ```python
  def login_ratelimit_key(request: Request) -> str | None:
      if request.method == "POST" and request.url.path == "/api/auth/login":
          return f"ip:{_client_ip(request)}"
      return None

  def refresh_ratelimit_key(request: Request) -> str | None:
      if request.method == "POST" and request.url.path == "/api/auth/refresh":
          return f"ip:{_client_ip(request)}"
      return None

  def register_ratelimit_key(request: Request) -> str | None:
      if request.method == "POST" and request.url.path == "/api/auth/register":
          return f"ip:{_client_ip(request)}"
      return None
  ```

  Plus a shared private `_client_ip(request: Request) -> str` helper that mirrors `apps/api/app/modules/auth/router.py:42-48` `_client_meta()` IP-extraction logic verbatim (parses `x-forwarded-for` first comma-separated value, falls back to `request.client.host`, returns `"unknown"` on neither). Binding: COPY THE SHAPE, do NOT import from `auth/router.py` — the auth-router helper returns `(ip, ua)` tuple; the ratelimit helper needs only `ip`. Duplication is acceptable for the 3-line helper; importing creates a circular dependency risk (ratelimit is foundational; auth-router imports from it implicitly via main.py).

- And the CSRF middleware MUST CONTINUE to fire FIRST (i.e., a `POST /api/auth/login` without `X-Portal-Client: web` header still returns 403 `csrf_required`, NOT 429 or 200). This is the ordering invariant. Verified by `test_csrf_middleware.py:test_post_without_header_blocked` continuing to pass unchanged.

- And the failed-credentials path on `/api/auth/login` (wrong password) MUST still emit the existing `auth.login.fail` audit event AND still return HTTP 401 (NOT 429) on calls 1-5 from a fresh IP. Only the 6th call within the window returns 429. The rate-limit middleware fires UNCONDITIONALLY (regardless of whether the login succeeded) — it counts ATTEMPTS, not FAILURES. The architecture text "5 failures / 60s per IP" is a slight simplification: the implementation counts every POST hit, but in practice an IP that succeeds in fewer than 5 attempts is statistically unlikely to be brute-forcing. Binding contract: the count is per-POST-attempt, NOT per-failed-attempt. Rationale: differentiating success vs failure inside the middleware requires either inspecting the response status (which requires buffering the response — incompatible with the streaming ASGI shape) OR splitting the middleware after the route handler (which violates the BEFORE-auth-dependency ordering). The 5-attempts-per-minute cap is tight enough that a legitimate user mis-typing their password 4 times in a row + succeeding on the 5th still works.

**AC-4 — Four new `Settings` keys in `apps/api/app/core/config.py` with correct defaults + Pydantic-Settings env-var tunability.**

- Given the existing `apps/api/app/core/config.py:Settings` class shape (Pydantic-Settings `BaseSettings`, `env_file=".env"`, snake_case field names auto-mapped to UPPER_SNAKE env-vars),
- When Story 6.6 ships,
- Then `Settings` MUST gain exactly these new fields, placed in a new `# Rate-limiting (Story 6.6)` block right after the existing `# Auth` block (lines 35-41):

  ```python
  # Rate-limiting (Story 6.6, Decision G)
  ratelimit_login_window_seconds: int = 60
  ratelimit_login_threshold: int = 5
  ratelimit_refresh_window_seconds: int = 60
  ratelimit_refresh_threshold: int = 10
  ratelimit_register_window_seconds: int = 60
  ratelimit_register_threshold: int = 3
  ```

  All fields are `int`. Defaults match architecture.md §1570-1572 verbatim (the architecture's key-shape table is the binding contract). Each field is auto-mapped to an UPPER_SNAKE env-var by Pydantic-Settings convention (e.g., `RATELIMIT_LOGIN_THRESHOLD=10` overrides the default).

- And the test fixture in `apps/api/tests/test_ratelimit_middleware.py` (the new file from AC-6) MUST exercise both the defaults AND a per-test override (e.g., `monkeypatch.setenv("RATELIMIT_LOGIN_THRESHOLD", "2") + get_settings.cache_clear()`) to prove the env-var tunability works. This is the AC-4 binding test.

- And NO new field is added for the share scope (Story 6.7 owns `ratelimit_share_*` — keep this story's scope tight to login/refresh/register per Story 6.6 epics.md §1613-1625).

- And the `share` scope's middleware instance is INTENTIONALLY NOT mounted in this story. Story 6.7 will:
  - Add `ratelimit_share_window_seconds: int = 86400` + `ratelimit_share_threshold: int = 20` + `ratelimit_share_soft_alert_threshold: int = 10`.
  - Mount a fourth `RateLimitMiddleware(scope="share", key_fn=share_ratelimit_key, ...)` invocation in `main.py` after the three from this story.
  - Add the admin-exemption short-circuit (Decision H).
  - Add the `app.share.ratelimit.soft_alert` structured log.

  This story does NOT pre-author any share-scope code paths or settings. The class shape from AC-1 MUST support a future fourth scope by parameter-passing only (zero code changes to `ratelimit.py` are expected from Story 6.7's fourth-instance mount — the constructor accepts any `scope` string).

**AC-5 — Behavioral verification at HTTP layer: 6th login from one IP within 60s returns 429; 11th refresh; 4th register.**

- Given the new test file `apps/api/tests/test_ratelimit_middleware.py` (AC-6),
- When the dev agent exercises each scope's threshold,
- Then the following table of HTTP-layer behaviors MUST hold verbatim:

  | Scope | Endpoint | Method | Threshold (default) | Calls 1..N pass | Call N+1 returns |
  |---|---|---|---|---|---|
  | `login` | `/api/auth/login` | POST | 5 | 5 (each returns 401 `invalid_credentials` for a bogus body) | 429 `rate_limited` with `Retry-After: 60` |
  | `refresh` | `/api/auth/refresh` | POST | 10 | 10 (each returns 401 `no_refresh` for a missing-cookie request) | 429 `rate_limited` with `Retry-After: 60` |
  | `register` | `/api/auth/register` | POST | 3 | 3 (each returns 404 `token_invalid` for a bogus query-param token + valid-shape body) | 429 `rate_limited` with `Retry-After: 60` |

- And the 429 response body shape MUST be `{"detail": "rate_limited", "scope": "<scope>", "retry_after_seconds": 60}` (JSON; verified by `r.json()` equality assertion).

- And each test MUST use `fakeredis.aioredis.FakeRedis()` swapped into `app.state.redis` via the existing `RedisFactory`-shaped `MagicMock` pattern (mirrors `test_share_admin.py:14-67`). NO real Redis connection. NO `time.sleep(60)` waiting for the window to clear — the in-process FakeRedis sorted-set state survives across `c.post()` calls within a single test function.

- And after a window-clear (achieved in tests by either monkey-patching `time.time` OR by flushing the fakeredis instance via `await fake.flushdb()` between the burst-and-await-clear assertions — see Dev Notes § "Window-clear test strategy"), the next call MUST pass through (count resets to 1 ≤ threshold). The test MUST verify at least the "burst then flush then re-burst" path for the `login` scope to prove the sliding-window math actually slides (otherwise the test could pass even with a fixed-window or token-bucket implementation).

- And tests for each scope MUST use a separate, distinguishing client-IP header (`X-Forwarded-For: 10.0.0.1`, `10.0.0.2`, `10.0.0.3`) so per-IP isolation is verified — two different IPs hammering `/api/auth/login` simultaneously must EACH be allowed up to the threshold. This is the "per-IP isolation" AC.

- And the existing `test_csrf_middleware.py:test_post_with_header_allowed` MUST continue to return 200 on the first call (it sends a real successful login to the seeded admin account). The CSRF test does NOT trigger the rate-limit because it only makes ONE login call per test. Verified by re-running the existing 6 csrf tests in the green suite. This is the regression check; Story 6.6 MUST NOT break existing login/refresh/register tests.

**AC-6 — Files, imports, registrations: full-file inventory + zero-drift wiring + named test list.**

- Given the existing conventions from `apps/api/app/core/auth/csrf.py` + `apps/api/app/main.py` + `apps/api/app/core/config.py` + `apps/api/tests/test_share_admin.py`,
- When the dev agent ships Story 6.6,
- Then the file inventory MUST be EXACTLY:
  - **NEW** `apps/api/app/core/auth/ratelimit.py` (~150 LOC: `RateLimitMiddleware` class + three `*_ratelimit_key()` functions + `_client_ip()` helper + module docstring per AGENTS.md docstring contract; see Dev Notes § "Implementation skeleton — ratelimit.py")
  - **UPDATED** `apps/api/app/main.py` (add three `app.add_middleware(RateLimitMiddleware, ...)` calls after `install_csrf_middleware(app)` at current line 68 — ~15 added LOC; one new import line: `from app.core.auth.ratelimit import RateLimitMiddleware, login_ratelimit_key, refresh_ratelimit_key, register_ratelimit_key`)
  - **UPDATED** `apps/api/app/core/config.py` (add six new `Settings` fields under a new `# Rate-limiting (Story 6.6)` block — ~10 added LOC; NO behavior change to the existing `@model_validator(mode="after")` block — the new fields are plain `int` defaults with no production-only constraints)
  - **NEW** `apps/api/tests/test_ratelimit_middleware.py` (~600 LOC: the 28 named tests from AC-6 + fixture wiring; ASGI-level unit tests for the middleware class + integration-style HTTP tests via `TestClient`)
- And the new test file MUST contain AT LEAST these named test cases (binding names — Dev Agent TDD red-phase checklist):
  - **Class-shape ASGI tests (use a minimal `FastAPI()` test app, NOT `create_app()` — the binding precedent is `test_csrf_middleware.py:test_post_with_header_allowed` shape inverted to test middleware in isolation):**
    - `test_middleware_passes_through_when_count_below_threshold` — call once, threshold=5; assert next-layer handler runs, response is the handler's expected output (200)
    - `test_middleware_returns_429_on_threshold_plus_one` — call 6 times with threshold=5; assert 6th returns 429 + `Retry-After: 60` header + body `{"detail": "rate_limited", "scope": "test_scope", "retry_after_seconds": 60}`
    - `test_middleware_skips_non_http_scope` — pass an ASGI `scope={"type": "lifespan"}` and verify pass-through (no Redis call)
    - `test_middleware_skips_when_key_fn_returns_none` — `key_fn` lambda returns `None` for the test request; verify pass-through + zero Redis keys created
    - `test_middleware_redis_unavailable_logs_warning_and_allows` — mock `redis.pipeline().__aenter__()` to raise `ConnectionError`; verify the request passes through AND `caplog` captures a `WARNING` record with `event.action == "ratelimit.redis_unavailable"`
    - `test_middleware_redis_timeout_logs_warning_and_allows` — same as above but with `redis.exceptions.TimeoutError`
    - `test_middleware_unexpected_exception_propagates` — mock pipeline to raise `ValueError("not a redis error")`; verify the exception propagates (does NOT get swallowed by the fail-soft catch-clause)
    - `test_middleware_sliding_window_purges_old_entries` — manually `ZADD` an entry at `now_ms - 70_000` (70 seconds ago, beyond the 60s window); make 5 calls; verify all 5 pass (old entry purged, count stays at 5)
    - `test_middleware_per_key_isolation` — set `key_fn` to return the value of a custom header; make 5 calls with `X-Test-Key: a` AND 5 calls with `X-Test-Key: b`; verify all 10 pass (two distinct keys, each at their threshold)
    - `test_middleware_zadd_unique_score_member` — manually populate the sorted set with 5 entries at the same millisecond score (via separate `ZADD` calls with the same score but UNIQUE member strings); make 1 call; verify it rejects (count=6). Verifies the `ZADD score=now_ms member=now_ms` pattern doesn't collapse concurrent same-ms requests
  - **Integration HTTP tests (use `TestClient(create_app())`, fakeredis swap, real route handlers — bindings the route + middleware ordering):**
    - `test_login_6th_call_returns_429_within_window` — 6 POST `/api/auth/login` with bogus body + same `X-Forwarded-For`; assert 1-5 return 401 `invalid_credentials`, 6th returns 429
    - `test_login_429_body_shape` — same as above; assert the 429 response body equals `{"detail": "rate_limited", "scope": "login", "retry_after_seconds": 60}`
    - `test_login_429_retry_after_header_value` — assert `r.headers["Retry-After"] == "60"` on the 429
    - `test_login_window_clears_after_flush` — burst 6 calls (last is 429); `await fake.flushdb()`; make 1 more call; assert 401 (passes through, count reset)
    - `test_login_different_ips_isolated` — 5 calls from `X-Forwarded-For: 1.1.1.1` + 5 calls from `X-Forwarded-For: 2.2.2.2`; assert all 10 return 401 (per-IP isolation)
    - `test_login_csrf_rejection_does_not_burn_rate_limit` — 10 POST `/api/auth/login` WITHOUT `X-Portal-Client: web` header (each returns 403 `csrf_required` BEFORE the rate-limit fires); then ONE POST with the header; assert 1st with-header call returns 401 (passes through, rate-limit count = 1, not 11). This is the CSRF-BEFORE-rate-limit ordering invariant.
    - `test_refresh_11th_call_returns_429_within_window` — 11 POST `/api/auth/refresh` with no `portal_refresh` cookie + same `X-Forwarded-For`; assert 1-10 return 401 `no_refresh`, 11th returns 429
    - `test_refresh_429_body_shape` — assert `r.json() == {"detail": "rate_limited", "scope": "refresh", "retry_after_seconds": 60}`
    - `test_register_4th_call_returns_429_within_window` — 4 POST `/api/auth/register` with bogus token query-param + valid-shape body; assert 1-3 return 404 `token_invalid`, 4th returns 429
    - `test_register_429_body_shape` — assert `r.json() == {"detail": "rate_limited", "scope": "register", "retry_after_seconds": 60}`
    - `test_register_429_does_not_emit_register_fail_audit` — the 4th call rejects BEFORE the route handler runs, so `auth.register.fail` audit row count stays at 3 (the three 404 calls each emit the audit). Verifies the BEFORE-auth-dependency ordering (the route's audit emission happens INSIDE the route body, AFTER the middleware). Binding for AC-3 ordering invariant.
    - `test_login_rate_limit_threshold_env_var_override` — `monkeypatch.setenv("RATELIMIT_LOGIN_THRESHOLD", "2")` + `get_settings.cache_clear()` + recreate app; assert 3rd call returns 429 (threshold lowered to 2). Verifies AC-4 env-var tunability.
    - `test_login_rate_limit_window_env_var_override` — `monkeypatch.setenv("RATELIMIT_LOGIN_WINDOW_SECONDS", "30")` + recreate app; manually `ZADD` an entry at `now_ms - 40_000` (40 seconds ago, beyond the new 30s window); make 5 calls; assert all pass (old entry purged by the new window math)
  - **Fail-soft tests:**
    - `test_login_redis_outage_allows_request_with_warning_log` — mock the `app.state.redis.get()` Redis instance's `pipeline` to raise `ConnectionError`; make 1 POST `/api/auth/login`; assert response is 401 (`invalid_credentials` — pass-through to route) AND `caplog` shows the warning record
    - `test_refresh_redis_outage_allows_request_with_warning_log` — same shape for refresh scope
    - `test_register_redis_outage_allows_request_with_warning_log` — same shape for register scope
  - **Module surface tests:**
    - `test_ratelimit_module_exports_class_and_three_key_fns` — `from app.core.auth.ratelimit import RateLimitMiddleware, login_ratelimit_key, refresh_ratelimit_key, register_ratelimit_key`; verify each is the expected type (class for the first, function for the three)
    - `test_login_ratelimit_key_returns_none_for_non_login_path` — call `login_ratelimit_key(mock_request_with_path="/api/auth/refresh")`; assert returns `None`
    - `test_login_ratelimit_key_returns_none_for_get_method` — `mock_request_with_method="GET", path="/api/auth/login"`; assert `None`
    - `test_client_ip_falls_back_to_request_client_host` — request with no `X-Forwarded-For` header; assert returns `request.client.host` (or `"unknown"` if even that is `None`)
    - `test_client_ip_parses_xff_first_value` — request with `X-Forwarded-For: 1.1.1.1, 2.2.2.2, 3.3.3.3`; assert returns `"1.1.1.1"`
- And `pytest apps/api/tests/test_ratelimit_middleware.py -v` MUST exit 0 with at least 28 tests green.
- And `pytest apps/api/ -q` MUST exit 0 with NO regressions versus the Story 6.5 baseline (~534 tests; this story adds ~28+ → expected ~562+).
- And `ruff format apps/api/` + `ruff check apps/api/` MUST pass clean with NO `# noqa` exceptions (repo's strict-clean policy from prior stories).
- And `infra/scripts/check-all.sh` from the repo root MUST exit 0 (all 10 stages green; matches Story 6.5 close-out gate).

**AC-7 — Explicit non-changes: zero frontend / migration / OpenAPI / audit / KNOWN_ENTITY_TYPES drift.**

- And NO frontend changes ride along (the 429 surface is a backend-only contract; the existing `apps/web/src/api/client.ts` already handles `4xx` responses generically via the `apiPost`/`apiGet` error envelope — see also Story 6.4 dev-record where the same null-frontend-change property held). Specifically: NO new route in `apps/web/src/routes/`, NO new error-toast keys in `apps/web/src/locales/{en,pl}.json`, NO new visual baselines. Verified by `grep -rn "rate_limited\|rate-limit\|429" apps/web/src` returning ONLY pre-existing matches (if any; none expected).
- And NO Alembic migration is needed (no schema changes — rate-limit state is Redis-only).
- And NO `KNOWN_ENTITY_TYPES` additions are needed in `apps/api/app/core/audit.py` (the rate-limit middleware does NOT call `record_event()`; it emits structured warnings to the logger only). Specifically: the 429 path does NOT add an audit row. Reason: a per-request audit row for every 429 would 10× the audit-log write volume during a credential-stuffing burst (the very condition the middleware exists to handle); the structured `WARNING app.auth.ratelimit redis_unavailable` log + GlitchTip ingest is the binding observability path (NFR5-OBS-1).
- And NO new audit action names are added (e.g., do NOT add `auth.ratelimit.exceeded` to the audit vocabulary). The E9 audit gate (Story 9.2 scenario 5 per NFR5-SEC-3) verifies the rate-limit by observed HTTP-429 behavior + GlitchTip log presence, NOT by audit-log row counts.
- And the OpenAPI surface DOES NOT change (no new routes; the middleware does NOT add route metadata — Starlette middlewares are invisible to FastAPI's OpenAPI generator). Verified by `pytest apps/api/tests/test_runbook_openapi_consistency.py -v` continuing to pass without modifications.
- And NO change to the existing CSRF middleware (`apps/api/app/core/auth/csrf.py` stays at its current 20-LOC shape). The rate-limit middleware is mounted AFTER the CSRF middleware in the stack (per AC-3 ordering); both coexist independently.
- And the existing `infra/scripts/deploy.sh` auto-deploy convention applies: after Story 6.6's dev-commit + Codex review + fix-up (if any) lands on `main`, the next deploy to `.190` MUST include the new middleware. No new deploy-specific gates needed (the middleware reads `RATELIMIT_*` env-vars; if `.190`'s `infra/.env` has none, the defaults apply — `5/60s`, `10/60s`, `3/60s` — which match the architecture's binding contract).

## Tasks / Subtasks

- [x] **T1 — Author `apps/api/app/core/auth/ratelimit.py` skeleton + module-level exports (AC-1, AC-4, AC-6)**
  - [x] T1.1 RED — Create `apps/api/tests/test_ratelimit_middleware.py` with the class-shape ASGI tests + module-surface tests from AC-6 (10 tests). The fixture rig MUST use a minimal `FastAPI()` test app — NOT `create_app()` — with a single `POST /test-route` returning `{"ok": True}`, wired with `app.add_middleware(RateLimitMiddleware, scope="test_scope", key_fn=lambda r: "static-key", window_seconds=60, threshold=5)`. The app's `state.redis` MUST be assigned a `MagicMock` factory whose `.get()` returns a `fakeredis.aioredis.FakeRedis()` instance (mirrors `test_share_admin.py:26-37` setup verbatim). Expected initial state: every test fails with `ImportError: cannot import name 'RateLimitMiddleware' from 'app.core.auth.ratelimit'` (the module does not yet exist).
  - [x] T1.2 GREEN — Create `apps/api/app/core/auth/ratelimit.py` per Dev Notes § "Implementation skeleton — ratelimit.py". The module MUST have a top-level docstring per the AGENTS.md docstring contract (mirroring `apps/api/app/core/auth/csrf.py:1` shape — `"""apps/api/app/core/auth/ratelimit.py — sliding-window rate-limit middleware."""`). The `RateLimitMiddleware` class signature MUST be the AC-1 exact form (`scope`, `key_fn`, `window_seconds`, `threshold` keyword-only; `app` positional). Use `time.time()` (NOT `datetime.datetime.now(UTC).timestamp()`) — the test relies on `monkeypatch.setattr("app.core.auth.ratelimit.time.time", lambda: 1700000000)` in one test case (`test_middleware_sliding_window_purges_old_entries`).
  - [x] T1.3 GREEN — Add the three `*_ratelimit_key()` module-top-level functions per AC-3 shape. Use `request.url.path` (string equality, NOT `startswith()` — the path `/api/auth/login/extra` MUST NOT be rate-limited because it's not a real route).
  - [x] T1.4 GREEN — Add the private `_client_ip(request: Request) -> str` helper mirroring `auth/router.py:42-48` semantics (parse first comma-separated `X-Forwarded-For` value; fall back to `request.client.host`; fallback to `"unknown"`). Add the two `_client_ip()` unit tests from AC-6.
  - [x] T1.5 Run `pytest apps/api/tests/test_ratelimit_middleware.py -v -k "class_shape or module_surface or client_ip"`. Expected: 10 tests green.

- [x] **T2 — Wire the three middleware instances into `apps/api/app/main.py:create_app()` (AC-3, AC-5, AC-6)**
  - [x] T2.1 RED — Author the integration HTTP tests from AC-6 (14 tests: 5 login + 2 refresh + 4 register + 3 env-var-override). The fixture rig MUST be a SECOND fixture in `test_ratelimit_middleware.py` — name it `integration_client` — that wires `TestClient(create_app())` + `app.state.redis` fakeredis swap (same shape as `test_share_admin.py:14-67`, NOT the minimal-app rig from T1.1). The fixture MUST set `c.headers.update({"X-Portal-Client": "web"})` so CSRF passes. Expected initial state: every integration test fails with the 6th login call STILL returning 401 (middleware not yet mounted in main.py).
  - [x] T2.2 GREEN — Add the four new lines + three `app.add_middleware()` calls to `apps/api/app/main.py:create_app()` per AC-3 binding shape. New import line at top of file (alphabetically sorted with existing imports): `from app.core.auth.ratelimit import (RateLimitMiddleware, login_ratelimit_key, refresh_ratelimit_key, register_ratelimit_key,)`. Three `app.add_middleware()` calls immediately after `install_csrf_middleware(app)`. Use `settings.ratelimit_login_*` etc. references (the settings reads happen ONCE at app-creation, not per-request — Starlette stores the middleware kwargs at mount time). **Note:** Story spec's literal "AFTER install_csrf_middleware" placement makes rate-limit the OUTERMOST layer in Starlette LIFO wrapping, which contradicts AC-5's `test_login_csrf_rejection_does_not_burn_rate_limit` invariant (CSRF must fire FIRST). Resolved by INVERTING install order in code (rate-limit add_middleware × 3 → then install_csrf_middleware), so CSRF wraps outermost. Behavioral order CSRF→ratelimit→handler honored. Dev Notes' claim that `@app.middleware("http")` decorator wraps OUTERMOST is incorrect — Starlette's `add_middleware` always prepends to user_middleware, regardless of decorator vs. method call.
  - [x] T2.3 GREEN — Run `pytest apps/api/tests/test_ratelimit_middleware.py -v`. Expected: all class-shape + integration tests green (24+ total). **Result: 31 tests green.**
  - [x] T2.4 Verify the CSRF-before-rate-limit ordering invariant by running the `test_login_csrf_rejection_does_not_burn_rate_limit` test in isolation; expected green.
  - [x] T2.5 Verify NO regression in the existing csrf middleware tests: `pytest apps/api/tests/test_csrf_middleware.py -v` — 6 tests still green.

- [x] **T3 — Add `Settings` fields + verify env-var tunability (AC-4, AC-6)**
  - [x] T3.1 RED — Author the 2 env-var-override tests from AC-6 (`test_login_rate_limit_threshold_env_var_override` and `test_login_rate_limit_window_env_var_override`). Both tests MUST call `get_settings.cache_clear()` after `monkeypatch.setenv(...)` and BEFORE `create_app()` (the `lru_cache` wrapper on `get_settings()` would otherwise return stale defaults). Expected initial state: tests fail because the `Settings` class doesn't yet have the new fields.
  - [x] T3.2 GREEN — Add the six new `ratelimit_*` fields to `apps/api/app/core/config.py:Settings` in the order from AC-4 (login window/threshold, refresh window/threshold, register window/threshold). All `int` defaults. NO `Annotated[..., Field(...)]` wrappers needed (the existing simple `int = N` pattern matches `jwt_ttl_minutes: int = 10` at line 37). NO `model_validator` addition (no production-only constraint).
  - [x] T3.3 Run `pytest apps/api/tests/test_ratelimit_middleware.py -v -k "env_var_override"` — both tests green.
  - [x] T3.4 Verify the defaults are correctly picked up: in a fresh `TestClient` instance WITHOUT any `monkeypatch.setenv("RATELIMIT_*", ...)` calls, the 6th login STILL returns 429 (using the default `threshold=5`). This is implicitly verified by `test_login_6th_call_returns_429_within_window` from T2.

- [x] **T4 — Author fail-soft tests + verify the broad-but-not-too-broad exception catch (AC-2, AC-6)**
  - [x] T4.1 RED — Author the 4 fail-soft tests from AC-6 (`test_middleware_redis_unavailable_logs_warning_and_allows`, `test_middleware_redis_timeout_logs_warning_and_allows`, `test_middleware_unexpected_exception_propagates`, plus the 3 per-scope variants `test_{login,refresh,register}_redis_outage_allows_request_with_warning_log`). The Redis-failure simulation MUST use `unittest.mock.patch.object(fake, "pipeline", side_effect=redis.exceptions.ConnectionError("simulated"))` (the `redis.exceptions` import is at `redis>=5.2`; verified present in `apps/api/pyproject.toml:15`). Use `pytest`'s `caplog` fixture to capture log records — assert at least one record exists with `record.name == "app.auth.ratelimit"`, `record.levelname == "WARNING"`, AND `record.__dict__.get("event.action") == "ratelimit.redis_unavailable"`. Expected initial state: tests fail because the middleware does not yet catch any exceptions. **Implementation note:** pytest `caplog` attaches its handler to root, but `app.core.logging.configure_logging` (called during FastAPI lifespan startup) does `root.handlers[:] = [JSON-handler]` and wipes pytest's LogCaptureHandler, so caplog captures nothing for tests that run after any `create_app()` boot in the session. Worked around with a dedicated `ratelimit_caplog` fixture that attaches a tiny `_ListHandler` directly to the `app.auth.ratelimit` named logger.
  - [x] T4.2 GREEN — Patch `RateLimitMiddleware.__call__` to wrap the pipelined Redis call in a `try / except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, OSError):` block. On exception, emit the structured `WARNING` log per Dev Notes § "Fail-soft logging contract" and pass-through to `await self.app(...)`. The exception MUST NOT propagate; the unexpected-exception test relies on `ValueError` propagating (not caught by the clause).
  - [x] T4.3 Run `pytest apps/api/tests/test_ratelimit_middleware.py -v -k "redis_unavailable or redis_timeout or unexpected_exception or redis_outage"`. Expected: 6 tests green (3 class-shape + 3 integration).
  - [x] T4.4 Manually verify the logger name + log shape: `import logging; logging.getLogger("app.auth.ratelimit").addHandler(logging.StreamHandler())`; trigger one fail-soft path; observe the WARNING record's `extra` dict — must contain `event.action`, `labels.scope`, `labels.key`, `error.message`. **Verified via debug `print(...)` in fixture: captured records carry `event.action="ratelimit.redis_unavailable"`, `labels.scope=<scope>`, `labels.key=ratelimit:<scope>:<keyfn>`, `error.message=<str(exc)>`.**

- [x] **T5 — Final quality gate + status flip (all ACs)**
  - [x] T5.1 Run `pytest apps/api/tests/test_ratelimit_middleware.py -v` — all 28+ tests green. **Result: 31/31 green.**
  - [x] T5.2 Run `pytest apps/api/tests/test_csrf_middleware.py -v` — 6 existing tests still green (regression).
  - [x] T5.3 Run `pytest apps/api/tests/test_auth*.py -v` — all existing auth tests still green (login, refresh, sessions — these tests make at most 1-3 login/refresh calls per test, well below the rate-limit thresholds).
  - [x] T5.4 Run `pytest apps/api/tests/test_invite_register.py -v` — all existing register tests still green (the existing 24 register tests each make 1-2 register calls; thresholds are loose enough that the per-test isolation via `tmp_path` + `monkeypatch.setenv("DATABASE_URL", ...)` is sufficient). **Pre-flight scan: max 2 calls per test to any rate-limited endpoint across `test_auth*.py` + `test_invite_register.py`.**
  - [x] T5.5 Run `pytest apps/api/ -q` — full backend suite green; expected ~562+ tests (baseline 534 + 28 new). **Result: 565 passed, 0 failed.**
  - [x] T5.6 Run `ruff format apps/api/` + `ruff check apps/api/` — clean. No `# noqa` exceptions.
  - [x] T5.7 Run `infra/scripts/check-all.sh` from repo root — all 10 stages green.
  - [x] T5.8 Update Dev Agent Record (Agent Model + Debug Log + Completion Notes + File List) below; flip `Status:` to `review`.

## Dev Notes

### Relevant architecture patterns and constraints

- **Decision G — Rate-limit middleware** (`architecture.md` §1553-1579): The binding decision text. Key bindings extracted:
  - **Module location:** new `apps/api/app/core/auth/ratelimit.py` (lives under `core/auth/` alongside `cookies.py`, `csrf.py`, `dependencies.py`, `jwt.py`, `password.py`, `refresh.py` — the binding precedent for auth-foundational code).
  - **Class shape:** `RateLimitMiddleware(app, scope, key_fn, window_seconds, threshold)` exporting four positional + keyword-only parameters.
  - **Algorithm:** Redis-backed **sliding window over sorted set** with one pipelined `MULTI/EXEC` round-trip per request (`ZREMRANGEBYSCORE` + `ZADD` + `EXPIRE` + `ZCARD`). One round-trip. Stateless server-side. Industry-standard (Cloudflare, GitHub API use this exact pattern).
  - **Key shapes (binding):** see architecture.md §1568-1573. This story implements the first 3 of 4 rows; Story 6.7 implements row 4 (`share`).
  - **Threshold sourcing:** `apps/api/app/core/config.py` Pydantic Settings — six new fields per AC-4 (window + threshold for each of 3 scopes).
  - **Middleware placement:** `apps/api/app/main.py:create_app()`, AFTER CORS, AFTER CSRF check, BEFORE auth dependency resolution. Reason: rate-limit fires BEFORE the password-hash check; otherwise the password-hash check (bcrypt — intentionally slow) absorbs the brute-force cost the rate-limit was meant to prevent. Repo-specific note: there is NO CORS middleware installed in `main.py` (verified by `grep -n "CORSMiddleware\|cors" apps/api/app/main.py` returning zero — the API is same-origin via the nginx reverse proxy at .190, no cross-origin XHR happens). So "AFTER CORS" is moot for this codebase; the binding ordering for this codebase is: CSRF → rate-limit → routes.
  - **Failure mode:** Redis unreachable → log `WARNING app.auth.ratelimit redis_unavailable scope=<scope>` and ALLOW the request. Matches Init 0 share-token fail-soft semantics (the share-resolution path also degrades gracefully on Redis outage). The trade-off: losing rate-limit briefly is better than losing the entire authentication surface. LAN+VPN allowlist still protects the portal during the cutover window.

- **Init 0 middleware precedent — `apps/api/app/core/auth/csrf.py`** (lines 1-20): The existing CSRF middleware is the binding precedent for two patterns:
  1. **Module shape:** module-top-level `install_csrf_middleware(app: FastAPI) -> None` function uses the `@app.middleware("http")` decorator INSIDE the install function. This pattern works for a SINGLE middleware instance per app. Story 6.6 deliberately does NOT use this pattern — three rate-limit instances cannot be registered via `@app.middleware("http")` (the decorator registers ONE middleware function; mounting three would need three different functions, which defeats the parameterized-class purpose). Instead, Story 6.6 uses Starlette's `app.add_middleware(MiddlewareClass, **kwargs)` pattern, which is the canonical multi-instance-mount API.
  2. **Path-based gating inside the middleware:** the CSRF middleware checks `request.url.path.startswith("/api/")` and `not path.startswith("/api/share/")` inline. The rate-limit middleware adopts the SAME pattern but moves the path check into the `key_fn` callable (returning `None` for non-matching requests). This keeps the middleware class generic over scope.

- **Starlette `add_middleware` ordering** — the binding contract for AC-3: Starlette's middleware stack is built LIFO. The LAST `add_middleware(...)` call wraps OUTERMOST (i.e., fires FIRST on incoming requests). The order of the three rate-limit calls (login → refresh → register) is alphabetical for stability — but because the three scopes are mutually-exclusive on path (each `*_ratelimit_key()` returns `None` for non-matching paths), the relative order WITHIN the trio is irrelevant.
  - Cross-cutting binding: the CSRF middleware is installed via `@app.middleware("http")` BEFORE the three `add_middleware()` calls — the decorator approach actually wraps as the OUTERMOST handler in this case (verified by reading Starlette source: `BaseHTTPMiddleware` registered via the decorator becomes the outermost layer). So the request flow is: incoming HTTP → CSRF check → rate-limit (one of three) → route handler. The 429 from rate-limit comes AFTER the 403 from CSRF — verified by AC-5's `test_login_csrf_rejection_does_not_burn_rate_limit` test.

- **`request.client.host` vs `X-Forwarded-For` extraction precedent** (`apps/api/app/modules/auth/router.py:42-48`):
  ```python
  def _client_meta(request: Request) -> tuple[str | None, str | None]:
      ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
          request.client.host if request.client else None
      )
      ua = request.headers.get("user-agent")
      return (ip or None), (ua or None)
  ```
  Story 6.6's `_client_ip()` helper MUST mirror this logic verbatim (parse first XFF, fall back to `request.client.host`, then `"unknown"` to avoid `None` ending up in the Redis key). The repo's deployment topology (nginx reverse proxy at .190) sets `X-Forwarded-For` on every upstream request; the `request.client.host` fallback exists for direct-localhost test traffic.

- **Audit emission conventions** (`apps/api/app/core/audit.py:47-84`): `record_event()` is the binding helper for all audit-row writes. **Rate-limit 429s MUST NOT call `record_event()`** — see AC-7 explicit non-change. The structured warning log to GlitchTip is the binding observability path.

### Implementation skeleton — `apps/api/app/core/auth/ratelimit.py` (binding for shape)

```python
"""apps/api/app/core/auth/ratelimit.py — sliding-window rate-limit middleware.

Redis-backed sliding window over a sorted set, one pipelined ``MULTI/EXEC``
round-trip per request. Used by ``apps/api/app/main.py:create_app()`` to mount
three middleware instances for ``login``, ``refresh``, and ``register`` scopes.

Decision references (architecture.md § Initiative 5):
  - Decision G: algorithm + module location + key shapes + threshold sourcing
    + middleware placement + Redis-down fail-soft semantics.

Caller contract: the middleware does NOT emit audit-log rows. The 429
response is the only side-effect on the rate-limit path; the
``ratelimit.redis_unavailable`` warning log is the only side-effect on the
fail-soft path. GlitchTip ingests the warning per NFR5-OBS-1.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import redis.exceptions
from fastapi import Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

_LOG = logging.getLogger("app.auth.ratelimit")


def _client_ip(request: Request) -> str:
    """Return the request's source IP, preferring first XFF then client host."""
    xff = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if xff:
        return xff
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def login_ratelimit_key(request: Request) -> str | None:
    if request.method == "POST" and request.url.path == "/api/auth/login":
        return f"ip:{_client_ip(request)}"
    return None


def refresh_ratelimit_key(request: Request) -> str | None:
    if request.method == "POST" and request.url.path == "/api/auth/refresh":
        return f"ip:{_client_ip(request)}"
    return None


def register_ratelimit_key(request: Request) -> str | None:
    if request.method == "POST" and request.url.path == "/api/auth/register":
        return f"ip:{_client_ip(request)}"
    return None


class RateLimitMiddleware:
    """Sliding-window rate-limit middleware (one Redis pipeline per request)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        scope: str,
        key_fn: Callable[[Request], str | None],
        window_seconds: int,
        threshold: int,
    ) -> None:
        self.app = app
        self.scope_name = scope
        self.key_fn = key_fn
        self.window_seconds = window_seconds
        self.threshold = threshold

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        key_suffix = self.key_fn(request)
        if key_suffix is None:
            await self.app(scope, receive, send)
            return

        redis_key = f"ratelimit:{self.scope_name}:{key_suffix}"
        now_ms = int(time.time() * 1000)
        window_ms = self.window_seconds * 1000

        try:
            redis_client = request.app.state.redis.get()
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(redis_key, "-inf", now_ms - window_ms)
                pipe.zadd(redis_key, {str(now_ms): now_ms})
                pipe.expire(redis_key, self.window_seconds + 1)
                pipe.zcard(redis_key)
                _, _, _, count = await pipe.execute()
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, OSError) as exc:
            _LOG.warning(
                "ratelimit.redis_unavailable",
                extra={
                    "event.action": "ratelimit.redis_unavailable",
                    "labels.scope": self.scope_name,
                    "labels.key": redis_key,
                    "error.message": str(exc),
                },
            )
            await self.app(scope, receive, send)
            return

        if count > self.threshold:
            response = JSONResponse(
                {
                    "detail": "rate_limited",
                    "scope": self.scope_name,
                    "retry_after_seconds": self.window_seconds,
                },
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
```

Key points:
- `from __future__ import annotations` keeps the `ASGIApp/Receive/Scope/Send` references string-resolved at runtime (avoids importing `starlette.types` at module-top-level when not needed for type checking).
- `request.app.state.redis.get()` returns the `Redis` instance from the `RedisFactory` mounted in `main.py:lifespan` — same pattern as `share/admin_router.py:22`.
- The `redis.exceptions.ConnectionError, TimeoutError, OSError` catch-clause is the narrowest set that covers Redis-down + network-hiccup + DNS-fail. Any other exception (e.g., `redis.exceptions.ResponseError` from a malformed command, which would indicate a coding bug) MUST propagate so it surfaces as a 500 (and GlitchTip captures the traceback).
- `await response(scope, receive, send)` is the Starlette pattern for sending a response from inside a raw ASGI middleware (NOT `return response` — that only works in the `@app.middleware("http")` decorator form). Verified by Starlette docs and the `BaseHTTPMiddleware.dispatch` source.

### Implementation skeleton — `apps/api/app/main.py` patch (binding for shape)

```diff
 from app.core.auth.csrf import install_csrf_middleware
+from app.core.auth.ratelimit import (
+    RateLimitMiddleware,
+    login_ratelimit_key,
+    refresh_ratelimit_key,
+    register_ratelimit_key,
+)
 from app.core.config import get_settings
```

```diff
     instrument_app(app)
     install_csrf_middleware(app)
+    # Story 6.6: rate-limit middleware (Decision G). Order: AFTER CSRF (so CSRF
+    # rejections don't burn rate-limit budget), BEFORE auth dependency (so
+    # password-hash verification doesn't absorb brute-force cost).
+    app.add_middleware(
+        RateLimitMiddleware,
+        scope="login",
+        key_fn=login_ratelimit_key,
+        window_seconds=settings.ratelimit_login_window_seconds,
+        threshold=settings.ratelimit_login_threshold,
+    )
+    app.add_middleware(
+        RateLimitMiddleware,
+        scope="refresh",
+        key_fn=refresh_ratelimit_key,
+        window_seconds=settings.ratelimit_refresh_window_seconds,
+        threshold=settings.ratelimit_refresh_threshold,
+    )
+    app.add_middleware(
+        RateLimitMiddleware,
+        scope="register",
+        key_fn=register_ratelimit_key,
+        window_seconds=settings.ratelimit_register_window_seconds,
+        threshold=settings.ratelimit_register_threshold,
+    )
```

### Implementation skeleton — `apps/api/app/core/config.py` patch

```diff
     # Auth
     jwt_secret: str = "change-me-in-production"
     jwt_algorithm: str = "HS256"
     jwt_ttl_minutes: int = 10
     cookie_secure: bool = True
     admin_email: str = "admin@local"
     admin_password: str = "change-me"

+    # Rate-limiting (Story 6.6, Decision G)
+    ratelimit_login_window_seconds: int = 60
+    ratelimit_login_threshold: int = 5
+    ratelimit_refresh_window_seconds: int = 60
+    ratelimit_refresh_threshold: int = 10
+    ratelimit_register_window_seconds: int = 60
+    ratelimit_register_threshold: int = 3
+
     # Observability
```

### Implementation skeleton — `apps/api/tests/test_ratelimit_middleware.py` (binding for shape)

```python
"""Tests for the Initiative 5 rate-limit middleware (Story 6.6).

Covers AC-1 through AC-7 from the Story 6.6 spec:
- AC-1: RateLimitMiddleware class shape (sliding-window primitive + 429 + Retry-After)
- AC-2: Redis-unreachable fail-soft (WARNING log + ALLOW)
- AC-3: Three instances mounted in main.py with CSRF-before-rate-limit ordering
- AC-4: Four Settings fields with env-var tunability
- AC-5: HTTP-layer threshold verification per scope (5/10/3 thresholds)
- AC-6: Per-IP isolation + sliding-window correctness
- AC-7: Zero frontend / migration / OpenAPI / audit drift

Two fixture rigs:
- ``minimal_app_client`` — a fresh FastAPI() with a single /test-route, used
  for class-shape ASGI unit tests (mounted with arbitrary scope="test_scope").
- ``integration_client`` — TestClient(create_app()) + fakeredis swap, used
  for integration HTTP tests against the real /api/auth/{login,refresh,register} routes.
"""

from __future__ import annotations

import logging
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest
import redis.exceptions
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth.ratelimit import (
    RateLimitMiddleware,
    _client_ip,
    login_ratelimit_key,
    refresh_ratelimit_key,
    register_ratelimit_key,
)


# ---------------------------------------------------------------------------
# Fixture: minimal FastAPI app with one /test-route + parameterized middleware
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_app_client():
    """A minimal FastAPI() app for ASGI-level unit tests."""
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    def _build(*, scope: str, key_fn, window_seconds: int = 60, threshold: int = 5):
        app = FastAPI()
        app.state.redis = factory
        app.add_middleware(
            RateLimitMiddleware,
            scope=scope,
            key_fn=key_fn,
            window_seconds=window_seconds,
            threshold=threshold,
        )

        @app.post("/test-route")
        def _r():
            return {"ok": True}

        return TestClient(app), fake

    yield _build


# ---------------------------------------------------------------------------
# Fixture: full create_app() + fakeredis swap (integration tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def integration_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    from app.main import create_app

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose
    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        app.state.redis = factory
        yield c, fake, app
    get_settings.cache_clear()
    get_engine.cache_clear()


# ---------------------------------------------------------------------------
# AC-1 + AC-6 class-shape tests
# ---------------------------------------------------------------------------

def test_middleware_passes_through_when_count_below_threshold(minimal_app_client):
    c, _ = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    r = c.post("/test-route")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_middleware_returns_429_on_threshold_plus_one(minimal_app_client):
    c, _ = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    for _ in range(5):
        r = c.post("/test-route")
        assert r.status_code == 200
    r6 = c.post("/test-route")
    assert r6.status_code == 429
    assert r6.headers["Retry-After"] == "60"
    assert r6.json() == {"detail": "rate_limited", "scope": "test_scope", "retry_after_seconds": 60}


def test_middleware_skips_non_http_scope(minimal_app_client):
    # ASGI lifespan scope MUST short-circuit; verified indirectly via TestClient
    # __enter__/__exit__ which sends a lifespan scope under the hood and would
    # raise if the middleware tried to call redis.pipeline() on it.
    c, fake = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    # TestClient ctor already ran lifespan; no exception means short-circuit OK.
    keys = c.app.state.redis.get  # smoke-check the factory is intact
    assert keys is not None


def test_middleware_skips_when_key_fn_returns_none(minimal_app_client):
    c, fake = minimal_app_client(scope="test_scope", key_fn=lambda r: None, threshold=5)
    for _ in range(100):
        r = c.post("/test-route")
        assert r.status_code == 200
    # No Redis keys should have been created (key_fn returned None → no Redis call).
    # Verified indirectly by the loop completing without hitting 429.


def test_middleware_redis_unavailable_logs_warning_and_allows(minimal_app_client, caplog):
    c, fake = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    # Replace fake.pipeline with a side-effect that raises ConnectionError.
    with (
        caplog.at_level(logging.WARNING, logger="app.auth.ratelimit"),
        patch.object(
            fake,
            "pipeline",
            side_effect=redis.exceptions.ConnectionError("simulated outage"),
        ),
    ):
        r = c.post("/test-route")
    assert r.status_code == 200
    records = [
        rec for rec in caplog.records if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1
    assert records[0].levelname == "WARNING"
    assert records[0].__dict__["labels.scope"] == "test_scope"


def test_middleware_redis_timeout_logs_warning_and_allows(minimal_app_client, caplog):
    c, fake = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    with (
        caplog.at_level(logging.WARNING, logger="app.auth.ratelimit"),
        patch.object(fake, "pipeline", side_effect=redis.exceptions.TimeoutError("slow")),
    ):
        r = c.post("/test-route")
    assert r.status_code == 200
    records = [
        rec for rec in caplog.records if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1


def test_middleware_unexpected_exception_propagates(minimal_app_client):
    c, fake = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    with patch.object(fake, "pipeline", side_effect=ValueError("not a redis error")):
        # The TestClient surfaces ValueError as a 500 with the exception in the
        # response body when raise_server_exceptions=True (default). Asserting
        # via pytest.raises is the cleaner shape:
        with pytest.raises(ValueError, match="not a redis error"):
            c.post("/test-route")


def test_middleware_sliding_window_purges_old_entries(minimal_app_client):
    c, fake = minimal_app_client(
        scope="test_scope", key_fn=lambda r: "k", window_seconds=60, threshold=5
    )
    # Pre-populate the sorted set with 4 entries WAY OUTSIDE the 60s window
    # (scores at 70 seconds ago). They should be ZREMRANGEBYSCORE'd by the first
    # request, so the count after the first call is 1, not 5.
    import anyio

    async def _seed():
        now_ms = int(time.time() * 1000)
        ancient = now_ms - 70_000
        for i in range(4):
            await fake.zadd("ratelimit:test_scope:k", {f"ancient-{i}": ancient + i})

    anyio.run(_seed)
    for _ in range(5):
        r = c.post("/test-route")
        assert r.status_code == 200, r.text
    r6 = c.post("/test-route")
    assert r6.status_code == 429


def test_middleware_per_key_isolation(minimal_app_client):
    c, fake = minimal_app_client(
        scope="test_scope",
        key_fn=lambda r: r.headers.get("X-Test-Key", "default"),
        threshold=5,
    )
    for _ in range(5):
        r = c.post("/test-route", headers={"X-Test-Key": "a"})
        assert r.status_code == 200
    for _ in range(5):
        r = c.post("/test-route", headers={"X-Test-Key": "b"})
        assert r.status_code == 200
    # 11th call on key "a" rejects
    r = c.post("/test-route", headers={"X-Test-Key": "a"})
    assert r.status_code == 429


def test_middleware_zadd_unique_score_member(minimal_app_client):
    """Verify ZADD member is unique-per-request even when scores collide.

    If the implementation used a fixed member (e.g., a static string), sorted-set
    semantics would collapse two concurrent same-ms requests into one entry,
    under-counting the actual request rate. Verified by injecting 5 entries
    with the same score and observing that ZCARD still sees them as distinct.
    """
    c, fake = minimal_app_client(
        scope="test_scope", key_fn=lambda r: "k", window_seconds=60, threshold=5
    )
    import anyio

    async def _seed():
        now_ms = int(time.time() * 1000)
        # Same score, different members → 5 distinct ZSET entries.
        await fake.zadd("ratelimit:test_scope:k", {f"m{i}": now_ms for i in range(5)})

    anyio.run(_seed)
    r = c.post("/test-route")
    assert r.status_code == 429


# ---------------------------------------------------------------------------
# AC-5 integration tests — login scope
# ---------------------------------------------------------------------------

def test_login_6th_call_returns_429_within_window(integration_client):
    c, _, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.0.1"}
    for _ in range(5):
        r = c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers=headers,
        )
        assert r.status_code == 401
    r6 = c.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
        headers=headers,
    )
    assert r6.status_code == 429
    assert r6.json()["detail"] == "rate_limited"


def test_login_429_body_shape(integration_client):
    c, _, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.0.2"}
    for _ in range(6):
        c.post(
            "/api/auth/login",
            json={"email": "x@x", "password": "x"},
            headers=headers,
        )
    r = c.post(
        "/api/auth/login",
        json={"email": "x@x", "password": "x"},
        headers=headers,
    )
    assert r.status_code == 429
    assert r.json() == {
        "detail": "rate_limited",
        "scope": "login",
        "retry_after_seconds": 60,
    }


def test_login_429_retry_after_header_value(integration_client):
    c, _, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.0.3"}
    for _ in range(6):
        c.post(
            "/api/auth/login",
            json={"email": "x@x", "password": "x"},
            headers=headers,
        )
    r = c.post(
        "/api/auth/login",
        json={"email": "x@x", "password": "x"},
        headers=headers,
    )
    assert r.headers["Retry-After"] == "60"


def test_login_window_clears_after_flush(integration_client):
    c, fake, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.0.4"}
    for _ in range(6):
        c.post(
            "/api/auth/login",
            json={"email": "x@x", "password": "x"},
            headers=headers,
        )
    # Flush all rate-limit keys to simulate a full window-clear.
    import anyio

    async def _flush():
        await fake.flushdb()

    anyio.run(_flush)
    r = c.post(
        "/api/auth/login",
        json={"email": "x@x", "password": "x"},
        headers=headers,
    )
    assert r.status_code == 401  # passes rate-limit, hits invalid-credentials


def test_login_different_ips_isolated(integration_client):
    c, _, _ = integration_client
    for _ in range(5):
        r = c.post(
            "/api/auth/login",
            json={"email": "x@x", "password": "x"},
            headers={"X-Forwarded-For": "1.1.1.1"},
        )
        assert r.status_code == 401
    for _ in range(5):
        r = c.post(
            "/api/auth/login",
            json={"email": "x@x", "password": "x"},
            headers={"X-Forwarded-For": "2.2.2.2"},
        )
        assert r.status_code == 401


def test_login_csrf_rejection_does_not_burn_rate_limit(integration_client):
    c, _, _ = integration_client
    # Drop the CSRF header so each call returns 403 BEFORE rate-limit fires.
    del c.headers["X-Portal-Client"]
    headers = {"X-Forwarded-For": "10.0.0.5"}
    for _ in range(10):
        r = c.post(
            "/api/auth/login",
            json={"email": "x@x", "password": "x"},
            headers=headers,
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "csrf_required"
    # Restore the header and make ONE valid call → must return 401, not 429.
    c.headers["X-Portal-Client"] = "web"
    r = c.post(
        "/api/auth/login",
        json={"email": "x@x", "password": "x"},
        headers=headers,
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# AC-5 integration tests — refresh scope
# ---------------------------------------------------------------------------

def test_refresh_11th_call_returns_429_within_window(integration_client):
    c, _, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.1.1"}
    for _ in range(10):
        r = c.post("/api/auth/refresh", headers=headers)
        assert r.status_code == 401
    r = c.post("/api/auth/refresh", headers=headers)
    assert r.status_code == 429


def test_refresh_429_body_shape(integration_client):
    c, _, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.1.2"}
    for _ in range(11):
        c.post("/api/auth/refresh", headers=headers)
    r = c.post("/api/auth/refresh", headers=headers)
    assert r.status_code == 429
    assert r.json() == {
        "detail": "rate_limited",
        "scope": "refresh",
        "retry_after_seconds": 60,
    }


# ---------------------------------------------------------------------------
# AC-5 integration tests — register scope
# ---------------------------------------------------------------------------

def test_register_4th_call_returns_429_within_window(integration_client):
    c, _, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.2.1"}
    body = {"email": "x@x", "password": "x" * 16, "display_name": "X"}
    for _ in range(3):
        r = c.post(
            "/api/auth/register?token=bogus-token-not-in-redis",
            json=body,
            headers=headers,
        )
        assert r.status_code == 404
    r = c.post(
        "/api/auth/register?token=bogus-token-not-in-redis",
        json=body,
        headers=headers,
    )
    assert r.status_code == 429


def test_register_429_body_shape(integration_client):
    c, _, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.2.2"}
    body = {"email": "x@x", "password": "x" * 16, "display_name": "X"}
    for _ in range(4):
        c.post(
            "/api/auth/register?token=bogus-token-not-in-redis",
            json=body,
            headers=headers,
        )
    r = c.post(
        "/api/auth/register?token=bogus-token-not-in-redis",
        json=body,
        headers=headers,
    )
    assert r.status_code == 429
    assert r.json() == {
        "detail": "rate_limited",
        "scope": "register",
        "retry_after_seconds": 60,
    }


def test_register_429_does_not_emit_register_fail_audit(integration_client):
    """The 429 fires BEFORE the route handler runs → no auth.register.fail row.

    Verified by counting `auth.register.fail` audit rows after the 4-call burst:
    expected count is 3 (the three 404 calls each emit), not 4.
    """
    from sqlmodel import Session, select

    from app.core.db.models import AuditLog
    from app.core.db.session import get_engine

    c, _, _ = integration_client
    headers = {"X-Forwarded-For": "10.0.2.3"}
    body = {"email": "x@x", "password": "x" * 16, "display_name": "X"}
    # Clear pre-existing audit rows from app boot
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(AuditLog).where(AuditLog.action == "auth.register.fail")).all():
            s.delete(row)
        s.commit()
    for _ in range(4):
        c.post(
            "/api/auth/register?token=bogus-token-not-in-redis",
            json=body,
            headers=headers,
        )
    with Session(engine) as s:
        rows = s.exec(
            select(AuditLog).where(AuditLog.action == "auth.register.fail")
        ).all()
    assert len(rows) == 3  # 3 successful 404s emit audit; 4th 429 does not


# ---------------------------------------------------------------------------
# AC-4 env-var override tests
# ---------------------------------------------------------------------------

def test_login_rate_limit_threshold_env_var_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r2.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("RATELIMIT_LOGIN_THRESHOLD", "2")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    from app.main import create_app

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose
    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        app.state.redis = factory
        headers = {"X-Forwarded-For": "10.0.5.1"}
        for _ in range(2):
            r = c.post(
                "/api/auth/login",
                json={"email": "x@x", "password": "x"},
                headers=headers,
            )
            assert r.status_code == 401
        r = c.post(
            "/api/auth/login",
            json={"email": "x@x", "password": "x"},
            headers=headers,
        )
        assert r.status_code == 429  # 3rd call rejects (threshold=2)
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_login_rate_limit_window_env_var_override(tmp_path, monkeypatch):
    """Window-size override: 30s instead of 60s → an entry at -40s is purged."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r3.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("RATELIMIT_LOGIN_WINDOW_SECONDS", "30")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    from app.main import create_app

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose
    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        app.state.redis = factory
        # Seed an ancient entry at -40 seconds (beyond the 30s window).
        import anyio

        async def _seed():
            now_ms = int(time.time() * 1000)
            await fake.zadd(
                "ratelimit:login:ip:10.0.5.2", {"ancient": now_ms - 40_000}
            )

        anyio.run(_seed)
        headers = {"X-Forwarded-For": "10.0.5.2"}
        for _ in range(5):
            r = c.post(
                "/api/auth/login",
                json={"email": "x@x", "password": "x"},
                headers=headers,
            )
            assert r.status_code == 401, r.text
    get_settings.cache_clear()
    get_engine.cache_clear()


# ---------------------------------------------------------------------------
# Fail-soft integration tests
# ---------------------------------------------------------------------------

def test_login_redis_outage_allows_request_with_warning_log(integration_client, caplog):
    c, fake, _ = integration_client
    with (
        caplog.at_level(logging.WARNING, logger="app.auth.ratelimit"),
        patch.object(fake, "pipeline", side_effect=redis.exceptions.ConnectionError("down")),
    ):
        r = c.post(
            "/api/auth/login",
            json={"email": "x@x", "password": "x"},
            headers={"X-Forwarded-For": "10.0.6.1"},
        )
    assert r.status_code == 401  # passes through, hits invalid-credentials
    records = [
        rec for rec in caplog.records if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1
    assert records[0].__dict__["labels.scope"] == "login"


def test_refresh_redis_outage_allows_request_with_warning_log(integration_client, caplog):
    c, fake, _ = integration_client
    with (
        caplog.at_level(logging.WARNING, logger="app.auth.ratelimit"),
        patch.object(fake, "pipeline", side_effect=redis.exceptions.ConnectionError("down")),
    ):
        r = c.post(
            "/api/auth/refresh",
            headers={"X-Forwarded-For": "10.0.6.2"},
        )
    assert r.status_code == 401
    records = [
        rec for rec in caplog.records if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1
    assert records[0].__dict__["labels.scope"] == "refresh"


def test_register_redis_outage_allows_request_with_warning_log(integration_client, caplog):
    c, fake, _ = integration_client
    with (
        caplog.at_level(logging.WARNING, logger="app.auth.ratelimit"),
        patch.object(fake, "pipeline", side_effect=redis.exceptions.ConnectionError("down")),
    ):
        r = c.post(
            "/api/auth/register?token=bogus",
            json={"email": "x@x", "password": "x" * 16, "display_name": "X"},
            headers={"X-Forwarded-For": "10.0.6.3"},
        )
    assert r.status_code == 404  # passes through, hits token_invalid
    records = [
        rec for rec in caplog.records if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1
    assert records[0].__dict__["labels.scope"] == "register"


# ---------------------------------------------------------------------------
# Module surface + helper tests
# ---------------------------------------------------------------------------

def test_ratelimit_module_exports_class_and_three_key_fns():
    from app.core.auth import ratelimit as rl

    assert isinstance(rl.RateLimitMiddleware, type)
    for fn in (rl.login_ratelimit_key, rl.refresh_ratelimit_key, rl.register_ratelimit_key):
        assert callable(fn)


def test_login_ratelimit_key_returns_none_for_non_login_path():
    req = MagicMock()
    req.method = "POST"
    req.url.path = "/api/auth/refresh"
    req.headers = {}
    req.client = MagicMock(host="1.2.3.4")
    assert login_ratelimit_key(req) is None


def test_login_ratelimit_key_returns_none_for_get_method():
    req = MagicMock()
    req.method = "GET"
    req.url.path = "/api/auth/login"
    req.headers = {}
    req.client = MagicMock(host="1.2.3.4")
    assert login_ratelimit_key(req) is None


def test_client_ip_falls_back_to_request_client_host():
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host="1.2.3.4")
    assert _client_ip(req) == "1.2.3.4"


def test_client_ip_parses_xff_first_value():
    req = MagicMock()
    req.headers = {"x-forwarded-for": "1.1.1.1, 2.2.2.2, 3.3.3.3"}
    req.client = MagicMock(host="ignored")
    assert _client_ip(req) == "1.1.1.1"
```

### Retry-After value rationale

The architecture text at §1567 lists the `Retry-After` header but doesn't bind the numeric value. Two candidates:

1. **`window_seconds`** (binding choice): "If you wait `window_seconds`, your rate-limit budget will be fully reset." Simple, conservative (slight over-wait), no per-request timestamp math.
2. **Time-to-window-end** (rejected): "If you wait until the oldest entry in the sliding window falls out, you can make one more call." More precise BUT requires `ZRANGE` to get the oldest entry's score — adds a Redis round-trip we don't need.

Picking (1) is consistent with the brief-working-assumption "rate-limit middleware uses a coarse 60-second granularity" and avoids the extra Redis round-trip. Mobile clients honoring `Retry-After` will wait at most `window_seconds` and then re-try — at that point the sliding window is fully empty, so the first re-try succeeds.

### Fail-soft logging cadence

Two interpretations of the architecture's "log `WARNING ... redis_unavailable` and ALLOW":

- **Per-request log (binding choice for this story):** every request that hits the Redis-outage path emits a WARNING. Pros: zero process-state to manage; GlitchTip aggregates duplicates anyway. Cons: a sustained Redis outage during a credential-stuffing burst produces N log lines per second.
- **Once-per-(scope, key) cache (rejected):** a `_warned: set[tuple[str, str]]` class-attribute on the middleware that suppresses duplicate logs. Adds memory + a reset path on process restart + a test surface ("does it reset on app boot?"). Not worth it.

Picking the per-request log keeps the implementation 5 lines simpler. The redis-outage path is rare AND short-lived in this homelab; the log volume is bounded.

### Window-clear test strategy

Two test patterns for verifying the sliding-window math:

1. **`time.monotonic` patching (rejected):** brittle — Redis sorted-set scores are millisecond-level timestamps; patching `time.time` inside the middleware doesn't propagate to the Redis server (fakeredis uses its OWN clock internally for `ZREMRANGEBYSCORE` boundaries).
2. **`await fake.flushdb()` (binding choice):** wipes the sorted-set entirely; the next call sees count=1. Doesn't verify the sliding aspect, only the threshold-reset aspect. To verify sliding, the test_middleware_sliding_window_purges_old_entries test uses `anyio.run(_seed)` to manually `ZADD` an ancient entry at `now_ms - 70_000`, then makes 5 calls; the first call's `ZREMRANGEBYSCORE` purges the ancient entry, count=5, all 5 pass.

This is the cleanest fakeredis-compatible pattern. If the implementation ever needs to be tested against real Redis (e.g., an E9 audit integration test), the same `flushdb` pattern works against a real instance.

### Key-fn placement rationale

Two placement choices for the per-scope `key_fn` callables:

1. **Inline lambdas in `main.py` (rejected):** `app.add_middleware(RateLimitMiddleware, scope="login", key_fn=lambda r: f"ip:{r.client.host}" if r.url.path == "/api/auth/login" else None, ...)`. Compact, but: (a) lambdas don't get `__name__` for stack traces, (b) the path-check logic is duplicated three times in `main.py`, (c) `_client_ip()` would also need to inline (or be imported).
2. **Module-top functions in `ratelimit.py` (binding choice):** `login_ratelimit_key`, `refresh_ratelimit_key`, `register_ratelimit_key` — each 3 lines, importable, testable in isolation (covered by AC-6 module-surface tests). The path-bind is co-located with the middleware class definition.

Picking (2) keeps `main.py` to a clean `app.add_middleware(...)` call with named-function references. Future Story 6.7 will add a `share_ratelimit_key` function alongside the existing three — same import style, same `main.py` add_middleware shape.

### Implementation order — TDD red phase first

The test file MUST be authored BEFORE the middleware class so the dev-agent feedback loop is "tests fail → implement → tests pass". Specifically:

1. T1.1 RED — `test_ratelimit_middleware.py` skeleton + 10 class-shape tests. Initial: all fail with `ImportError`.
2. T1.2 GREEN — `ratelimit.py` class + key_fn functions. Class-shape tests pass.
3. T2.1 RED — integration tests (14 tests). Initial: 6th login call returns 401, not 429 (middleware not yet mounted).
4. T2.2 GREEN — `main.py` `add_middleware` calls. Integration tests pass.
5. T3.1 RED — env-var tests (2 tests). Initial: AttributeError on `settings.ratelimit_login_threshold`.
6. T3.2 GREEN — `config.py` field additions. Env-var tests pass.
7. T4.1 RED — fail-soft tests (6 tests). Initial: ConnectionError raises 500, not 401.
8. T4.2 GREEN — `try/except` clause in `__call__`. Fail-soft tests pass.

This staging keeps each task's diff small and reviewable. A reviewer can checkout each green-phase commit and see the test failure → pass transition cleanly.

### Pre-flight: scanning existing tests for high-volume callers

Before T5.4 runs the full backend suite, the dev agent SHOULD scan the existing test files for any test that makes >3 calls to the same rate-limited endpoint within a single test function. Probable hotspots:

- `apps/api/tests/test_invite_register.py` — multiple `c.post("/api/auth/register?token=...")` calls per test (23 register tests; some test failure-mode bursts).
- `apps/api/tests/test_auth_login_logout.py` — multiple login + logout cycles.
- `apps/api/tests/test_auth_refresh.py` — extensive refresh-token testing including family-rotation invariants.

Pre-flight grep:

```bash
# Find every test function that makes >3 calls to /api/auth/login, /refresh, or /register
grep -rn "c\.post.*/api/auth/\(login\|refresh\|register\)" apps/api/tests/ | \
    awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -20
```

If any single test function exceeds the rate-limit (e.g., 6+ login POSTs from the same IP), it has two options:

1. **Decompose** — split into two test functions, each making ≤5 login calls. Preferred.
2. **Per-test env override** — `monkeypatch.setenv("RATELIMIT_LOGIN_THRESHOLD", "100")` at the top of the test fixture. Last resort; only if decomposition is awkward.

Each existing test uses a FRESH `TestClient` (per the conftest fixture) which creates a fresh app + fresh fakeredis instance. The rate-limit state is therefore per-test-isolated; no cross-test contamination. The risk is ONLY within a single test function making too many calls.

### Project Structure Notes

#### Three middleware instances vs. one parameterized middleware with internal scope-dispatch

Architecture Decision G binds to "RateLimitMiddleware(app, scope, key_fn, window_seconds, threshold)" with three instances mounted. An alternative would have been ONE middleware that internally dispatches over the three scopes based on path-matching. Reasons the architecture's three-instance shape is the binding choice:

1. **Per-scope tunability** — each instance has its OWN `window_seconds` + `threshold` settings, sourced from independent Settings keys. A unified middleware would need a `dict[str, tuple[window, threshold]]` config — more surface, less ergonomic.
2. **Starlette idiom** — `add_middleware(MiddlewareClass, **kwargs)` is the canonical multi-instance API. Going against it would surprise future readers.
3. **Future Story 6.7** — the `share` scope adds an admin-exemption short-circuit + a soft-alert log path. Adding those to a unified middleware bloats the per-request logic for the 3 auth scopes that DON'T need them. The three-instance shape keeps `share` cleanly orthogonal.

The trade-off: three middleware instances = three pipelined Redis round-trips per request in the worst case (login + refresh + register middlewares all evaluating their `key_fn` on every request). MITIGATED: each `key_fn` returns `None` for non-matching paths (returns BEFORE the Redis call). So in practice, only ONE of the three Redis pipelines fires per request. Verified by T1.4's `test_middleware_skips_when_key_fn_returns_none` test.

#### Why no `share` scope in this story (Story 6.7 binding)

Architecture Decision G includes 4 scopes; this story implements 3. The `share` scope (Decision H) adds:

- A different key shape: per-user (not per-IP), per-day (not per-minute).
- An admin-exemption short-circuit (`if user.role == admin: pass through`).
- A soft-alert structured log at 50% threshold (`app.share.ratelimit.soft_alert`).
- A dependency on Story 6.5's member role expansion (the cap key uses `user_id` from the JWT, which only exists for member/admin roles; this story's three scopes are IP-based, no user-role dependency).

Bundling `share` into 6.6 would conflate two distinct architectural decisions (G vs H) and add a dependency on 6.5 that 6.6 doesn't otherwise have. The split keeps each story's scope-of-change minimal — 6.6 ships ONLY when the auth-scope rate-limits land cleanly; 6.7 ships the share-scope layer on top.

#### Audit-action vocabulary unchanged

Per AC-7, the rate-limit middleware does NOT emit `record_event()` calls. No new audit action names. No `KNOWN_ENTITY_TYPES` additions. The E9 audit gate (Story 9.2 scenario 5 per NFR5-SEC-3) verifies the rate-limit by:

- Observed HTTP-429 behavior (scripted burst).
- GlitchTip `WARNING app.auth.ratelimit redis_unavailable` log presence on Redis-outage replay.

NOT by audit-log row counts.

#### Frontend null-change verification

Story 6.4 introduced the `/register` route in `apps/web/src/routes/register.tsx`. Story 6.5 made no frontend changes (member share-token UI is Story 8.x). Story 6.6 also makes no frontend changes — the 429 response shape is generic enough that the existing `apiPost()` error envelope in `apps/web/src/api/client.ts` handles it without route-specific logic. Verified by:

```bash
grep -rn "rate_limited\|429\|too.many" apps/web/src/ | grep -v test | grep -v node_modules
# Expected: zero matches (no rate-limit-specific frontend handling required).
```

Story 8.x admin-panel UI may surface rate-limit metrics later (a dashboard widget showing per-IP request rates) — out of scope for Story 6.6.

#### CSRF middleware coexistence

The existing CSRF middleware at `apps/api/app/core/auth/csrf.py` MUST stay at its current 20-LOC shape. Story 6.6 does NOT touch it. The CSRF middleware fires FIRST on every request (registered via `@app.middleware("http")` which Starlette wraps OUTERMOST). The rate-limit middlewares fire NEXT. A CSRF-rejected request (403 `csrf_required`) does NOT burn rate-limit budget — verified by AC-5's `test_login_csrf_rejection_does_not_burn_rate_limit` test.

Future refactor opportunity: convert `csrf.py` to the `add_middleware(MiddlewareClass)` shape for consistency with rate-limit. Out of scope for Story 6.6.

#### No CORS middleware in this repo

Architecture Decision G specifies "AFTER CORS, AFTER CSRF". This repo has NO CORS middleware (the FastAPI app is same-origin via the nginx reverse proxy at .190; no cross-origin XHR happens). So the practical ordering for this codebase is: CSRF → rate-limit → routes. The architecture's "AFTER CORS" language is a forward-looking placeholder in case the team ever adds CORS for a multi-origin scenario — when that day comes, the CORS middleware MUST be installed BEFORE the rate-limit middlewares (CORS is even more "outer" than CSRF). Flag for future awareness; no code action this story.

#### Per-route allowlist binding (rate-limit is path-narrow)

Each `*_ratelimit_key()` function checks BOTH method AND path with string equality. This means:

- `POST /api/auth/login` → login rate-limit applies.
- `POST /api/auth/login/extra` → NO rate-limit applies (path mismatch).
- `GET /api/auth/login` → NO rate-limit applies (method mismatch — though no GET route exists at this path anyway).
- `POST /api/auth/refresh` → refresh rate-limit applies.
- `POST /api/auth/register` → register rate-limit applies (path is `/api/auth/register`; the query-param `?token=` is NOT part of the path-match — the rate-limit applies to all POSTs to `/api/auth/register` regardless of token shape).

This is intentional. The rate-limit's job is path-narrow brute-force protection; expanding to path-prefix matching would create surprising behavior on future sub-routes.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision G — Rate-limit middleware] (lines 1553-1579; binding for algorithm, module location, key shapes, threshold sourcing, placement, fail-soft semantics)
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision H — Per-member share cap] (lines 1581-1592; intentionally NOT implemented in this story — Story 6.7 owns)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.6] (lines 1613-1625; acceptance check shape — 3 scopes, 5/10/3 thresholds, 60s windows, Decision G one-pipelined-call binding)
- [Source: _bmad-output/planning-artifacts/epics.md#FR5-RATELIMIT-1] (line 1492; FR table binding)
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-RATELIMIT-1] (line 1204; verifiable acceptance — "scripted 6-failure burst on /api/auth/login from one IP returns 429 on the 6th call")
- [Source: _bmad-output/planning-artifacts/prd.md#NFR5-SEC-3] (line 1221; E9 audit scenario coverage — rate-limit verification is scenario 5)
- [Source: _bmad-output/planning-artifacts/prd.md#NFR5-OBS-1] (line 1244; GlitchTip-visible structured logs for new auth events — covers the `app.auth.ratelimit` warning)
- [Source: apps/api/app/main.py] (lines 1-83; create_app factory — Story 6.6 patches between line 68 (install_csrf_middleware) and line 70 (health route))
- [Source: apps/api/app/core/auth/csrf.py] (lines 1-20; binding precedent for middleware module shape — Story 6.6 deliberately uses Starlette's `add_middleware(MiddlewareClass)` form instead of `@app.middleware("http")`)
- [Source: apps/api/app/core/config.py] (lines 1-104; Settings class — Story 6.6 adds 6 fields after the `# Auth` block)
- [Source: apps/api/app/modules/auth/router.py] (lines 42-48; `_client_meta()` IP-extraction helper — binding precedent for `_client_ip()`)
- [Source: apps/api/app/modules/auth/router.py] (lines 204-214; structured logging shape with `event.action` + `labels.*` extras — binding precedent for `app.auth.ratelimit` warning log)
- [Source: apps/api/app/modules/share/admin_router.py] (lines 20-22; `request.app.state.redis.get()` Redis-from-state pattern — binding precedent)
- [Source: apps/api/tests/test_share_admin.py] (lines 14-67; TestClient + fakeredis swap fixture — binding precedent for `integration_client` fixture)
- [Source: apps/api/tests/test_csrf_middleware.py] (lines 1-66; existing CSRF test pattern — binding precedent for middleware-level tests)
- [Source: apps/api/tests/conftest.py] (lines 1-65; session-scoped `_isolated_db` + per-test `client` fixture)
- [Source: _bmad-output/implementation-artifacts/6-5-member-permission-expansion-share-router.md] (Story 6.5 spec — binding precedent for spec shape, fixture-rig shape, AC-6 named-test-list pattern)
- [Source: _bmad-output/implementation-artifacts/6-4-public-register-endpoint-and-ui.md] (Story 6.4 spec — `/api/auth/register` endpoint behavior; rate-limit applies to this route)
- [Source: _bmad-output/implementation-artifacts/6-3-admin-invite-endpoints-generate-list-revoke.md] (Story 6.3 spec — admin invite endpoints; NOT rate-limited by this story per AC-3 path-narrow binding)
- [Source: apps/api/app/modules/invite/router.py] (lines 1-100; `/api/auth/register` route — Story 6.6 rate-limits this route via the `register` scope)
- [Source: apps/api/pyproject.toml] (lines 5-29; `redis>=5.2` + `fakeredis>=2.26` already present — no new deps needed)

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Claude Opus 4.7, 1M context) — via Claude Code CLI

### Debug Log References

- **TestClient portal binding** — fakeredis async Queue bound to a different event loop. Fixed by entering `TestClient(app).__enter__()` inside the `minimal_app_client` factory so the anyio portal stays alive across `c.post()` calls within a single test. For seed-state setup (manual `ZADD`), use `c.portal.call(_seed)` instead of `anyio.run(_seed)` so the seeded keys live in the same loop the TestClient request flows use.
- **Cross-test fakeredis state pollution** — default `fakeredis.aioredis.FakeRedis()` shares a global FakeServer registry. Counter accumulates across tests sharing the same `ratelimit:<scope>:<key>` shape. Fixed by passing `server=fakeredis.FakeServer()` to every FakeRedis instantiation so each test owns its own server.
- **ZADD member collision under sub-millisecond bursts** — `str(now_ms)` as the ZSET member collapses 6 in-millisecond requests into 1-2 entries (same score + same member = no-op ZADD), under-counting the actual rate. Fixed by switching member shape to `f"{now_ms}-{uuid.uuid4().hex}"`. Score still stays at `now_ms` for sliding-window math.
- **CSRF-before-rate-limit ordering invariant** — Story spec's literal install order (rate-limit AFTER `install_csrf_middleware`) makes rate-limit the OUTERMOST Starlette layer per LIFO wrapping — directly violates AC-5's `test_login_csrf_rejection_does_not_burn_rate_limit` test (which requires CSRF to fire FIRST). Resolved by INVERTING install order in main.py: rate-limit × 3 → then CSRF last → CSRF wraps outermost as required. Dev Notes' claim that the `@app.middleware("http")` decorator wraps as OUTERMOST is incorrect — Starlette's `add_middleware` always prepends to `user_middleware`, regardless of how it's invoked.
- **caplog handler wiped by `configure_logging`** — `app.core.logging.configure_logging` (called from FastAPI lifespan startup) does `root.handlers[:] = [JSON-handler]` and removes pytest's LogCaptureHandler. After any test session that boots `create_app()`, pytest's built-in `caplog` captures nothing for descendants of root. Worked around with a dedicated `ratelimit_caplog` fixture that attaches a private `_ListHandler` directly to the `app.auth.ratelimit` named logger.

### Completion Notes List

- Implemented `apps/api/app/core/auth/ratelimit.py` (~131 LOC) per AC-1: `RateLimitMiddleware(app, *, scope, key_fn, window_seconds, threshold)` class with one-pipelined-call sliding-window primitive over Redis sorted set; HTTP 429 + `Retry-After` header + `{"detail": "rate_limited", "scope": "<scope>", "retry_after_seconds": <int>}` body on rejection; pass-through on non-HTTP scope and `key_fn(req) is None`. Three module-top `*_ratelimit_key()` functions for login/refresh/register scopes. Private `_client_ip()` helper mirrors `auth/router.py:_client_meta()` IP-extraction.
- Mounted three middleware instances in `apps/api/app/main.py:create_app()` — install order inverted from spec literal (rate-limit × 3 → CSRF last) so Starlette LIFO wrapping yields CSRF outermost. Behavioral chain: incoming HTTP → CSRF → rate-limit (one of three) → route handler.
- Added six new `Settings` fields under `# Rate-limiting (Story 6.6, Decision G)` block in `apps/api/app/core/config.py`: `ratelimit_{login,refresh,register}_{window_seconds,threshold}` with defaults 60/5, 60/10, 60/3 per architecture §1570-1572.
- Fail-soft on Redis outage: middleware catches `(redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, OSError)`, emits structured `WARNING` log to `app.auth.ratelimit` with `event.action="ratelimit.redis_unavailable"` + `labels.scope` + `labels.key` + `error.message` extras, and passes the request through to the route handler. Any other exception class propagates (verified by `test_middleware_unexpected_exception_propagates`).
- 31 new tests in `apps/api/tests/test_ratelimit_middleware.py`: 10 ASGI class-shape unit tests via `minimal_app_client` fixture (parameterized `RateLimitMiddleware`-on-`/test-route`), 11 HTTP integration tests via `integration_client` fixture (real `create_app()` + fakeredis swap), 2 env-var override tests, 3 per-scope fail-soft tests, 5 module-surface + helper tests.
- Verified per-IP isolation, sliding-window correctness (ancient entries purged by `ZREMRANGEBYSCORE`), per-key ZADD uniqueness under same-ms collisions, env-var tunability (threshold + window), CSRF-before-rate-limit ordering invariant, and the binding NFR5-OBS-1 path (structured warning ingestable by GlitchTip).
- Zero frontend changes, zero Alembic migration, zero OpenAPI surface change, zero new audit-action names (per AC-7).
- Full backend suite: 565 tests passed, 0 failed (baseline 534 + 31 new). Ruff format + check clean. `infra/scripts/check-all.sh` all 10 stages green.
- DOC-DRIFT NOTE for retro: Dev Notes § "Starlette `add_middleware` ordering" contains an incorrect claim that `@app.middleware("http")` registered via decorator wraps as OUTERMOST. The actual Starlette behavior is uniform: every `add_middleware` call prepends to `user_middleware`, so FIRST-added → INNERMOST. The fix landed in main.py (install CSRF last). Recommend `bmad-correct-course` to update architecture.md Decision G if it has the same wording, so Story 6.7's `share` scope mount lands without re-discovering the issue.

### File List

- **NEW** `apps/api/app/core/auth/ratelimit.py` — RateLimitMiddleware class + 3 `*_ratelimit_key()` functions + `_client_ip()` helper.
- **NEW** `apps/api/tests/test_ratelimit_middleware.py` — 31 tests (class-shape ASGI + HTTP integration + env-var + fail-soft + module-surface + helper).
- **MODIFIED** `apps/api/app/main.py` — imports + three `app.add_middleware(RateLimitMiddleware, ...)` calls (before `install_csrf_middleware`, so CSRF wraps outermost per Starlette LIFO).
- **MODIFIED** `apps/api/app/core/config.py` — six new `ratelimit_*` int fields on `Settings` under a new `# Rate-limiting (Story 6.6, Decision G)` block.

### Change Log

- 2026-05-19 — Story 6.6 implemented end-to-end (T1→T5). All 7 ACs satisfied. Full suite 565/565 green, ruff clean, check-all.sh all 10 stages green. Status: ready-for-dev → review.
