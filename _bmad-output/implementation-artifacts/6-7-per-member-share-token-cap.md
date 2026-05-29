# Story 6.7: Per-member share-token cap — extend `ratelimit.py` with `share` scope + soft-alert + admin exemption

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want a fourth `RateLimitMiddleware` instance mounted in `apps/api/app/main.py:create_app()` with scope `share`, key shape `ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}` (UTC day boundary), 86400s window, 20-creations hard threshold, 10-creations soft-alert threshold, JWT-cookie-derived `user_id` extraction, **admin role exemption short-circuit**, soft-alert structured log on logger `app.share.ratelimit` at the 10th creation (`event.action="share.ratelimit.soft_alert"` with `{user_id, role, count, threshold, window_end}` payload visible in GlitchTip per NFR5-OBS-1), HTTP 429 hard-fail on the 21st creation with `Retry-After: <seconds-until-next-UTC-midnight>` header, scope binding to `POST /api/admin/share` ONLY (`GET /api/admin/share` admin-only listing and `DELETE /api/admin/share/{token}` admin-only revoke are NOT capped per Decision H scope rule; `GET /share/{token}` anonymous consumption is not in this router), realized by extending the existing `RateLimitMiddleware` class with two new optional keyword-only constructor params (`soft_alert_threshold: int | None = None`, `retry_after_seconds_fn: Callable[[int], int] | None = None`) plus three new `Settings` keys (`ratelimit_share_window_seconds: int = 86400`, `ratelimit_share_threshold: int = 20`, `ratelimit_share_soft_alert_threshold: int = 10`) plus one new module-top callable `share_ratelimit_key(request)` in `apps/api/app/core/auth/ratelimit.py` that decodes the `portal_access` JWT cookie locally (no FastAPI dependency injection — the middleware runs BEFORE auth-dependency resolution per Decision G ordering) and returns `None` for non-POST methods / non-`/api/admin/share` paths / missing-or-invalid JWT / `admin` role (the architecture's "single `if user.role == Role.admin: return await call_next(request)` line" expressed inside `share_ratelimit_key`) so that the brief working-assumption "Member share-link generation is a deliberate amplification surface" is closed off, the E9 audit gate (NFR5-SEC-3, Story 9.2 audit scenario 6 — "scripted 21-share-creation burst from one member account") has a concrete subject to verify against, and EVERY currently-passing test in `apps/api/tests/` continues to pass unchanged (the existing 18 Story 6.5 share-member-permission tests + 31 Story 6.6 rate-limit middleware tests + 565-test backend baseline MUST stay green — only NEW tests in `apps/api/tests/test_ratelimit_share_cap.py` author 10th-soft-alert + 21st-hard-fail + admin-exemption + UTC-day-roll + Retry-After-to-midnight assertions).

## Acceptance Criteria

**AC-1 — Extend `RateLimitMiddleware` class with `soft_alert_threshold` + `retry_after_seconds_fn` keyword-only params (backward-compatible; trio mount sites unchanged).**

- Given the existing `apps/api/app/core/auth/ratelimit.py:RateLimitMiddleware.__init__` signature from Story 6.6 (`app`, `scope`, `key_fn`, `window_seconds`, `threshold` — all four kw-only after `app`),
- When Story 6.7 ships,
- Then the constructor MUST gain exactly these two new keyword-only parameters, both defaulting to `None` (zero behavioral change for the three existing trio instances — login/refresh/register continue to use `Retry-After: <window_seconds>` and emit NO soft-alert log):

  ```python
  class RateLimitMiddleware:
      def __init__(
          self,
          app: ASGIApp,
          *,
          scope: str,
          key_fn: Callable[[Request], str | None],
          window_seconds: int,
          threshold: int,
          soft_alert_threshold: int | None = None,
          retry_after_seconds_fn: Callable[[], int] | None = None,
      ) -> None: ...
  ```

  Both params are stored on the instance verbatim (`self.soft_alert_threshold`, `self.retry_after_seconds_fn`).

- And the `__call__` method's rejection path MUST compute `retry_after_seconds` as `self.retry_after_seconds_fn() if self.retry_after_seconds_fn else self.window_seconds`. This preserves the 6.6 behavior verbatim for login/refresh/register (no `retry_after_seconds_fn` passed → falls back to `self.window_seconds`) and gives Story 6.7's share instance a hook to compute "seconds until next UTC midnight" at rejection time (NOT at construction time — the value drifts as the day progresses).

- And the `__call__` method's NON-rejection (count ≤ threshold) path MUST emit the soft-alert log when, and ONLY when, BOTH conditions hold:
  - `self.soft_alert_threshold is not None`
  - the per-request `count` (the ZCARD result from the pipelined Redis round-trip) equals `self.soft_alert_threshold` EXACTLY (strict equality — fires once per crossing per key per process-lifetime; the 9th request emits no log, the 10th emits one log, the 11th–20th emit no logs, the 21st rejects with 429).

  The log MUST go to the logger named `app.share.ratelimit` (NEW logger; distinct from the existing `app.auth.ratelimit` used for the redis_unavailable warning — Decision H architecture text uses `app.share.ratelimit.soft_alert` as the structured event name, decomposed here as logger=`app.share.ratelimit` + event.action=`share.ratelimit.soft_alert`). The log call MUST be:

  ```python
  _SHARE_LOG = logging.getLogger("app.share.ratelimit")
  ...
  if (
      self.soft_alert_threshold is not None
      and count == self.soft_alert_threshold
  ):
      _SHARE_LOG.warning(
          "share.ratelimit.soft_alert",
          extra={
              "event.action": "share.ratelimit.soft_alert",
              "labels.scope": self.scope_name,
              "labels.key": redis_key,
              "labels.count": count,
              "labels.threshold": self.threshold,
              "labels.soft_alert_threshold": self.soft_alert_threshold,
          },
      )
  ```

  Severity `WARNING` (not INFO) — GlitchTip's default ingest threshold per NFR5-OBS-1 picks up WARNING-and-above; INFO would silently drop into logs-only. This matches Story 6.6's redis_unavailable WARNING precedent.

- And the soft-alert MUST emit BEFORE the `await self.app(...)` pass-through (i.e., the log fires regardless of whether the route handler ultimately succeeds — count==10 means "the 10th POST hit the middleware", and that signal is what operators want surfaced). The Redis ZADD has already incremented the count by the time `count == 10` is observed; the request proceeds to the route handler normally and (assuming valid payload) returns 201.

**AC-2 — `share_ratelimit_key(request)` callable: path match + JWT decode + admin exemption + member key shape.**

- Given the existing `apps/api/app/core/auth/ratelimit.py` module-top callables `login_ratelimit_key` / `refresh_ratelimit_key` / `register_ratelimit_key` (binding precedent for shape — each returns `str | None`),
- When Story 6.7 ships,
- Then a new module-top callable MUST be added with this exact shape:

  ```python
  from datetime import UTC, datetime

  from app.core.auth.cookies import ACCESS_COOKIE
  from app.core.auth.jwt import TokenError, decode_token
  from app.core.config import get_settings


  def share_ratelimit_key(request: Request) -> str | None:
      if request.method != "POST" or request.url.path != "/api/admin/share":
          return None
      token = request.cookies.get(ACCESS_COOKIE)
      if not token:
          return None
      try:
          claims = decode_token(token, secret=get_settings().jwt_secret)
      except TokenError:
          return None
      role = claims.get("role")
      if role == "admin":
          return None  # Decision H admin exemption — operator self-DoS prevention
      if role != "member":
          return None  # agent / unknown-role → let auth dependency reject with 403/401
      user_id = claims.get("sub")
      if not user_id:
          return None
      today_utc = datetime.now(UTC).strftime("%Y-%m-%d")
      return f"user:{user_id}:day:{today_utc}"
  ```

  Binding bullet-points:
  - **Path:** EXACT string equality on `/api/admin/share` (NOT `startswith` — the path `/api/admin/share/foo/bar` MUST NOT be rate-limited because `POST /api/admin/share/{token}` is not a real route; `DELETE /api/admin/share/{token}` IS a real route per Decision H scope, but DELETE on this path is rejected by the method check). Doc-drift: architecture.md §1589 + epics.md §1631 text both write `POST /api/share/` but the code's actual share-router prefix is `/api/admin/share` (Story 6.5 already flagged this drift; resolution remains deferred to `bmad-correct-course`). Story 6.7 uses the CORRECT path verbatim from the live router (`apps/api/app/modules/share/admin_router.py:18` — `prefix="/api/admin/share"`); the spec captures the drift in Project Structure Notes for the post-ship retro.
  - **Cookie name:** `portal_access` (re-exported as `ACCESS_COOKIE` from `apps/api/app/core/auth/cookies.py:7`).
  - **JWT decode error path:** `TokenError` → return `None`. Reason: the middleware MUST NOT 401 — that's the route handler's job (the existing `current_member_or_admin` dependency returns 401 `missing_access` / `invalid_access` / `access_expired`). Returning `None` skips the rate-limit count; the route handler then issues the correct 401/403 with the correct error code.
  - **Admin exemption:** `role == "admin"` → return `None`. This is the architecture's "single `if user.role == Role.admin: return await call_next(request)` line" expressed inside the key_fn (cleaner than wedging role inspection into the middleware class — keeps `RateLimitMiddleware` scope-agnostic). The exemption applies ONLY to the `share` scope (admin remains subject to `login`/`refresh`/`register` rate-limits per Decision H closing sentence).
  - **Non-member / non-admin / missing-sub:** return `None`. The auth dependency in the share router will reject with 403 `member_or_admin_required`. The middleware does not duplicate that check; it merely abstains from counting.
  - **Member key suffix:** `user:{user_id}:day:{YYYY-MM-DD}` where `YYYY-MM-DD` is UTC-derived via `datetime.now(UTC).strftime("%Y-%m-%d")`. This matches the architecture.md §1573 + §1585 binding table entry verbatim. Combined with the middleware's `f"ratelimit:{scope_name}:{key_suffix}"` prefix in `__call__`, the final Redis key is `ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}`.

- And `share_ratelimit_key` MUST NOT cache the `get_settings()` result at module-import time. The call lives inside the function body so the test fixture's `monkeypatch.setenv("JWT_SECRET", ...) + get_settings.cache_clear()` pattern works against per-test isolation.

- And NO new import dependency on `app.core.auth.dependencies` or `app.modules.share.*` is introduced (would create a circular-import risk; ratelimit.py is auth-foundational like csrf.py).

**AC-3 — Fourth middleware instance mounted in `apps/api/app/main.py:create_app()` (placement: between the trio and the CSRF install; alphabetical with trio for stability).**

- Given the existing `apps/api/app/main.py:create_app()` middleware install sequence from Story 6.6 (lines 73-103 — three `app.add_middleware(RateLimitMiddleware, ...)` calls in alphabetical order login → refresh → register, then `install_csrf_middleware(app)` LAST so CSRF wraps OUTERMOST per Starlette LIFO),
- When Story 6.7 ships,
- Then `main.py:create_app()` MUST add a FOURTH `app.add_middleware(RateLimitMiddleware, ...)` call placed AFTER the existing three rate-limit calls and BEFORE `install_csrf_middleware(app)`. The call MUST be:

  ```python
  app.add_middleware(
      RateLimitMiddleware,
      scope="share",
      key_fn=share_ratelimit_key,
      window_seconds=settings.ratelimit_share_window_seconds,
      threshold=settings.ratelimit_share_threshold,
      soft_alert_threshold=settings.ratelimit_share_soft_alert_threshold,
      retry_after_seconds_fn=share_retry_after_seconds,
  )
  ```

  Position rationale: relative order WITHIN the four rate-limit instances is irrelevant (their `key_fn` callables are mutually exclusive on path — each returns `None` for any non-matching request). Alphabetical ordering (login, refresh, register, share) is kept for diff-readability. The CSRF middleware MUST stay LAST in the install sequence (i.e., OUTERMOST in Starlette's LIFO stack) so `test_login_csrf_rejection_does_not_burn_rate_limit` (Story 6.6 AC-5) continues to hold for the share scope too — a `POST /api/admin/share` without `X-Portal-Client: web` header MUST still return 403 `csrf_required` and NOT burn the share-cap budget.

- And the import line at the top of `main.py` MUST be expanded to include the two new exports from ratelimit.py:

  ```python
  from app.core.auth.ratelimit import (
      RateLimitMiddleware,
      login_ratelimit_key,
      refresh_ratelimit_key,
      register_ratelimit_key,
      share_ratelimit_key,            # NEW
      share_retry_after_seconds,      # NEW
  )
  ```

- And `share_retry_after_seconds` MUST be a module-top callable in `apps/api/app/core/auth/ratelimit.py` returning `int` (seconds until next UTC midnight):

  ```python
  def share_retry_after_seconds() -> int:
      """Seconds remaining until the next UTC midnight (next day boundary)."""
      now = datetime.now(UTC)
      tomorrow = (now + timedelta(days=1)).replace(
          hour=0, minute=0, second=0, microsecond=0
      )
      return max(int((tomorrow - now).total_seconds()), 1)
  ```

  The `max(..., 1)` clamp avoids a corner-case 0/-1 if the function is called within the same microsecond as midnight rollover (defensive — clock skew across the Redis client and the API process shouldn't matter for the integer second value, but `Retry-After: 0` is interpreted as "retry immediately" by HTTP clients, which would defeat the purpose). NO `timezone.utc` import — use `datetime.UTC` (Python 3.11+ idiom; matches `apps/api/app/modules/share/service.py:3` precedent).

- And the share middleware mount MUST NOT regress the existing CSRF-before-rate-limit ordering. New regression check: `pytest apps/api/tests/test_ratelimit_middleware.py::test_login_csrf_rejection_does_not_burn_rate_limit -v` MUST still pass unchanged.

**AC-4 — Three new `Settings` keys in `apps/api/app/core/config.py` (window=86400s, threshold=20, soft_alert_threshold=10) with env-var tunability.**

- Given the existing Story 6.6 `# Rate-limiting (Story 6.6, Decision G)` block in `apps/api/app/core/config.py:Settings` (lines 42-48 — six `int` fields),
- When Story 6.7 ships,
- Then `Settings` MUST gain exactly these three new fields, placed immediately after the Story 6.6 block (extending the same `# Rate-limiting` section, NOT a new section — these are part of the same Decision G/H middleware family):

  ```python
  # Rate-limiting (Story 6.6, Decision G)
  ratelimit_login_window_seconds: int = 60
  ratelimit_login_threshold: int = 5
  ratelimit_refresh_window_seconds: int = 60
  ratelimit_refresh_threshold: int = 10
  ratelimit_register_window_seconds: int = 60
  ratelimit_register_threshold: int = 3
  # Rate-limiting (Story 6.7, Decision H — per-member share cap)
  ratelimit_share_window_seconds: int = 86400
  ratelimit_share_threshold: int = 20
  ratelimit_share_soft_alert_threshold: int = 10
  ```

  All `int`. Defaults match architecture.md §1573 (window=86400s, threshold=20) + §1587 (soft_alert_threshold=10) verbatim. Each field auto-maps to UPPER_SNAKE env-var by Pydantic-Settings convention (e.g., `RATELIMIT_SHARE_THRESHOLD=5` overrides the default for fast iteration on `.190`).

- And `infra/env.example` MUST gain three commented-out reference lines under the existing Story 6.6 ratelimit comments (lines 14-19 — matching the existing pattern verbatim):

  ```
  # RATELIMIT_SHARE_WINDOW_SECONDS=86400
  # RATELIMIT_SHARE_THRESHOLD=20
  # RATELIMIT_SHARE_SOFT_ALERT_THRESHOLD=10
  ```

  Commented-out because the defaults are the binding architecture values; explicit overrides are an ops-only knob (e.g., to lower threshold to 5 during E9 audit smoke for faster scenario coverage).

- And NO behavioral change to the existing `@model_validator(mode="after")` block (`_block_default_secrets_in_prod`) — the new fields are plain `int` defaults with no production-only constraint.

- And NO `infra/docker-compose.yml` change is required (the Story 6.6 rate-limit env-vars were not wired into compose either; the Pydantic Settings `env_file=".env"` autoload handles them in production; defaults apply if `.env` omits them).

**AC-5 — Behavioral verification: HTTP-layer member 21st share returns 429 with `Retry-After`-to-midnight; member 10th share emits soft-alert log; admin 21st share returns 201; non-POST methods + non-share paths uncapped.**

- Given the new test file `apps/api/tests/test_ratelimit_share_cap.py` (AC-6),
- When the dev agent exercises the share scope,
- Then the following table of HTTP-layer behaviors MUST hold verbatim:

  | Case | Cookie | Path | Method | Iterations | Expected |
  |---|---|---|---|---|---|
  | Member happy path 1-20 | `member_token` | `/api/admin/share` | POST | 20 sequential | each returns 201 with fresh `token` |
  | Member 21st rejection | `member_token` | `/api/admin/share` | POST | 21st in same UTC day | 429 with body `{"detail":"rate_limited","scope":"share","retry_after_seconds":<N>}` AND `Retry-After: <N>` header where `N == share_retry_after_seconds()` ± 5 (clock-drift tolerance) |
  | Member 10th soft-alert | `member_token` | `/api/admin/share` | POST | 10th in same UTC day | returns 201 (NOT 429 — soft-alert is log-only) AND captured log on `app.share.ratelimit` logger with `event.action == "share.ratelimit.soft_alert"` |
  | Member 9th + 11th no-log | `member_token` | `/api/admin/share` | POST | 9th and 11th calls separately | each returns 201 AND NO soft-alert log emitted (strict-equality check on the 10th only) |
  | Admin 21st exempt | `admin_token` | `/api/admin/share` | POST | 21st in same UTC day | 201 (admin exemption — key_fn returns `None` → no count) |
  | Member DELETE not capped | `admin_token` (DELETE is admin-only per Decision C) | `/api/admin/share/{token}` | DELETE | 25 sequential | each returns 204 (DELETE on share router; never rate-limited by `share` scope because `share_ratelimit_key` returns `None` for non-POST) |
  | Member GET list not capped | `admin_token` (GET list admin-only per Decision C) | `/api/admin/share` | GET | 25 sequential | each returns 200 (GET method check in key_fn returns `None`) |
  | Anonymous POST not capped by share scope | (no cookie) | `/api/admin/share` | POST | 25 sequential | each returns 401 `missing_access` (auth dep rejection — middleware abstains) AND share-scope Redis key shows zero entries |
  | UTC-day rollover resets | `member_token` | `/api/admin/share` | POST | 21st call after monkeypatched UTC date advance | returns 201 (new day → new Redis key → count resets to 1) |
  | Per-user isolation | two distinct `member_token` cookies | `/api/admin/share` | POST | 20 from member-A + 20 from member-B | all 40 return 201 (per-user Redis keys, no cross-contamination) |

- And the soft-alert log payload MUST contain ALL of: `event.action == "share.ratelimit.soft_alert"`, `labels.scope == "share"`, `labels.key` starting with `"ratelimit:share:user:"`, `labels.count == 10`, `labels.threshold == 20`, `labels.soft_alert_threshold == 10`. Asserted in `test_member_10th_share_emits_soft_alert_log`.

- And the `Retry-After: <N>` integer MUST be **within ±5 seconds** of the freshly-computed `share_retry_after_seconds()` at assertion time (sliding-second tolerance — the test must not flake at a midnight rollover). The test asserts `1 <= int(r.headers["Retry-After"]) <= 86_400` AND `abs(int(r.headers["Retry-After"]) - share_retry_after_seconds()) <= 5`.

- And the existing Story 6.5 share-member-permission tests (18 tests in `test_share_member_permission.py`) MUST continue to pass unchanged. The Story 6.5 happy-path test (`test_member_post_share_returns_201`) hits POST `/api/admin/share` exactly ONCE — well below the 20-threshold — so no rate-limit interaction. Verified by `pytest apps/api/tests/test_share_member_permission.py -v` returning 18 passed.

- And the existing Story 6.6 rate-limit tests (31 tests in `test_ratelimit_middleware.py`) MUST continue to pass unchanged. The trio's middleware behavior is untouched — the new `soft_alert_threshold` and `retry_after_seconds_fn` params default to `None`, preserving 6.6 semantics. Verified by `pytest apps/api/tests/test_ratelimit_middleware.py -v` returning 31 passed.

**AC-6 — Files, imports, registrations: full-file inventory + zero-drift wiring + named test list.**

- Given the existing conventions from `apps/api/app/core/auth/ratelimit.py` (Story 6.6) + `apps/api/tests/test_ratelimit_middleware.py` (Story 6.6) + `apps/api/tests/test_share_member_permission.py` (Story 6.5),
- When the dev agent ships Story 6.7,
- Then the file inventory MUST be EXACTLY:
  - **UPDATED** `apps/api/app/core/auth/ratelimit.py` (~80 added LOC: two new constructor params on `RateLimitMiddleware` + soft-alert emission block in `__call__` + `share_ratelimit_key` callable + `share_retry_after_seconds` callable + new `_SHARE_LOG` module global + new imports: `datetime.UTC`, `datetime.datetime`, `datetime.timedelta`, `app.core.auth.cookies.ACCESS_COOKIE`, `app.core.auth.jwt.TokenError`, `app.core.auth.jwt.decode_token`, `app.core.config.get_settings`)
  - **UPDATED** `apps/api/app/main.py` (~12 added LOC: import expansion + one new `app.add_middleware(RateLimitMiddleware, scope="share", ...)` block; placement between existing trio and `install_csrf_middleware(app)`)
  - **UPDATED** `apps/api/app/core/config.py` (~3 added LOC: three new `ratelimit_share_*` fields in the rate-limiting block; one new `# Rate-limiting (Story 6.7, Decision H — per-member share cap)` comment line)
  - **UPDATED** `infra/env.example` (~3 added LOC: three commented-out `RATELIMIT_SHARE_*` reference lines under the existing Story 6.6 ratelimit comments)
  - **NEW** `apps/api/tests/test_ratelimit_share_cap.py` (~750 LOC: 22+ named tests covering AC-1..AC-7; reuses the `test_share_member_permission.py:client` fixture shape verbatim — seeded admin + seeded member User row + member-role JWT cookie + admin-role JWT cookie + Model rows + fakeredis swap)
- And the new test file MUST contain AT LEAST these named test cases (binding names — Dev Agent TDD red-phase checklist):
  - **Class-shape / param-shape tests (extend `RateLimitMiddleware` introspection):**
    - `test_middleware_accepts_soft_alert_threshold_kw_only` — construct `RateLimitMiddleware(test_app, scope="x", key_fn=lambda r: "k", window_seconds=60, threshold=20, soft_alert_threshold=10)`; assert `mw.soft_alert_threshold == 10` and the default `retry_after_seconds_fn is None`
    - `test_middleware_accepts_retry_after_seconds_fn_kw_only` — construct with `retry_after_seconds_fn=lambda: 42`; assert `mw.retry_after_seconds_fn() == 42`
    - `test_middleware_backward_compat_no_new_params` — construct WITHOUT the two new params; assert `mw.soft_alert_threshold is None` AND `mw.retry_after_seconds_fn is None` (Story 6.6 trio instances are constructed this way — proves zero behavioral drift)
    - `test_middleware_soft_alert_emits_at_exact_threshold` — construct with `threshold=20, soft_alert_threshold=10`; make 11 requests (keys=fixed); assert ONLY the 10th request triggers a log record on `app.share.ratelimit` logger (the 9th and 11th do NOT)
    - `test_middleware_soft_alert_payload_shape` — same as above; on the 10th request, assert the captured log record's `__dict__` contains `event.action == "share.ratelimit.soft_alert"`, `labels.scope == "x"`, `labels.count == 10`, `labels.threshold == 20`, `labels.soft_alert_threshold == 10`
    - `test_middleware_soft_alert_does_not_emit_when_disabled` — construct with `soft_alert_threshold=None` (default); make 100 requests; assert ZERO records on `app.share.ratelimit` logger
    - `test_middleware_retry_after_seconds_fn_takes_precedence` — construct with `window_seconds=60, retry_after_seconds_fn=lambda: 3600`; trigger 429; assert `r.headers["Retry-After"] == "3600"` (NOT "60") AND `r.json()["retry_after_seconds"] == 3600`
    - `test_middleware_retry_after_seconds_fn_default_falls_back_to_window` — construct WITHOUT `retry_after_seconds_fn` (Story 6.6 shape); trigger 429; assert `r.headers["Retry-After"] == "60"` (= window_seconds) — regression check
  - **`share_ratelimit_key` callable tests (use a `MagicMock`-shaped Request OR a minimal test `Request(scope=..., receive=...)` factory):**
    - `test_share_key_returns_none_for_non_post_method` — request with `method="GET", url.path="/api/admin/share"`; assert returns `None`
    - `test_share_key_returns_none_for_non_share_path` — request with `method="POST", url.path="/api/admin/users"`; assert returns `None`
    - `test_share_key_returns_none_for_missing_cookie` — `method="POST", url.path="/api/admin/share"`, no `portal_access` cookie; assert returns `None`
    - `test_share_key_returns_none_for_invalid_jwt` — same as above, `portal_access="not-a-real-jwt"`; assert returns `None`
    - `test_share_key_returns_none_for_admin_role` — valid `portal_access` JWT with `role="admin"`; assert returns `None` (the Decision H exemption verifier)
    - `test_share_key_returns_none_for_agent_role` — valid `portal_access` JWT with `role="agent"`; assert returns `None` (agent has no share permission anyway; let the auth dep return 403)
    - `test_share_key_returns_user_day_for_member` — valid `portal_access` JWT with `role="member", sub=<uuid>`; assert returns `f"user:{uuid}:day:{YYYY-MM-DD}"` where `YYYY-MM-DD` matches today's UTC date
    - `test_share_key_uses_utc_day_boundary` — monkeypatch `datetime.datetime.now` to return `2026-01-01T23:30:00+00:00` (just before UTC midnight) AND `2026-01-02T00:30:00+00:00` (just after UTC midnight); assert the returned suffix changes between the two calls (`day:2026-01-01` → `day:2026-01-02`)
  - **`share_retry_after_seconds` callable tests:**
    - `test_share_retry_after_seconds_returns_positive_int` — call directly; assert `1 <= result <= 86_400`
    - `test_share_retry_after_seconds_decreases_as_day_progresses` — monkeypatch `datetime.datetime.now` to return two timestamps 1 hour apart; assert the second result is ~3600 lower than the first
    - `test_share_retry_after_seconds_clamps_to_one_at_midnight_corner` — monkeypatch `datetime.datetime.now` to return exactly midnight UTC; assert result `>= 1` (the `max(..., 1)` clamp)
  - **Integration HTTP tests (use `TestClient(create_app())` + fakeredis swap + seeded admin + seeded member; mirror `test_share_member_permission.py:client` fixture shape):**
    - `test_member_first_20_share_creations_return_201` — member-cookie + 20 sequential POST `/api/admin/share`; assert each returns 201 with a fresh `token` field
    - `test_member_21st_share_creation_returns_429` — same as above + 21st call; assert `r.status_code == 429` AND `r.json() == {"detail":"rate_limited","scope":"share","retry_after_seconds":<int>}` AND `r.headers["Retry-After"] == r.json()["retry_after_seconds"].__str__()`
    - `test_member_21st_share_retry_after_within_5s_of_midnight` — same as above; assert `abs(int(r.headers["Retry-After"]) - share_retry_after_seconds()) <= 5`
    - `test_member_10th_share_emits_soft_alert_log` — member-cookie + 10 sequential POST `/api/admin/share`; on the 10th call, assert: (a) `r.status_code == 201` (soft-alert is log-only, NOT 429); (b) captured log records on `app.share.ratelimit` include exactly 1 record with `event.action == "share.ratelimit.soft_alert"` AND `labels.count == 10`
    - `test_member_9th_share_does_not_emit_soft_alert` — 9 POST; assert ZERO records on `app.share.ratelimit` (strict-equality check)
    - `test_member_11th_share_does_not_emit_soft_alert` — 11 POST; assert EXACTLY 1 record (the 10th); the 11th call MUST NOT re-emit
    - `test_admin_21st_share_creation_returns_201` — admin-cookie + 21 sequential POST `/api/admin/share`; assert ALL return 201 (admin exemption per Decision H); assert ZERO entries in any `ratelimit:share:user:*` Redis key (verified via `await fake.keys("ratelimit:share:*")` returning empty)
    - `test_member_get_list_share_returns_403_not_429` — member-cookie + 25 sequential GET `/api/admin/share`; assert ALL 25 return 403 `admin_required` (Story 6.5 per-route allowlist) — confirms GET method check in `share_ratelimit_key` returns `None`, NOT capped by share scope
    - `test_admin_delete_share_not_capped` — admin-cookie + 25 sequential DELETE `/api/admin/share/{token}` (each token freshly minted by a preceding POST); assert each DELETE returns 204; assert ZERO entries in any `ratelimit:share:user:*` Redis key (DELETE method check in `share_ratelimit_key` returns `None`)
    - `test_anonymous_post_share_returns_401_not_429` — no cookie + 25 sequential POST `/api/admin/share`; assert ALL 25 return 401 `missing_access` (auth dep rejection); assert ZERO entries in any `ratelimit:share:user:*` Redis key
    - `test_share_csrf_rejection_does_not_burn_cap` — member-cookie + drop `X-Portal-Client: web` header + 25 sequential POST; assert each returns 403 `csrf_required` (CSRF wraps OUTERMOST); restore the header + 1 valid POST; assert returns 201 with rate-limit count = 1 (NOT 26 — CSRF rejections did NOT burn cap)
    - `test_share_per_user_isolation` — seed TWO members A and B; 20 POST from A + 20 POST from B; assert all 40 return 201; the 21st from A returns 429; the 21st from B returns 429 (per-user keys, no cross-contamination)
    - `test_share_utc_day_rollover_resets_count` — member-cookie + 20 POST today (Redis key `day:2026-05-19`); monkeypatch `datetime.datetime.now` to advance UTC date to `2026-05-20`; 1 POST; assert returns 201 (new day → new Redis key → count starts fresh at 1)
    - `test_share_threshold_env_var_override` — `monkeypatch.setenv("RATELIMIT_SHARE_THRESHOLD", "5")` + `get_settings.cache_clear()` + recreate app; member-cookie + 6 POST; assert 1-5 return 201, 6th returns 429
    - `test_share_soft_alert_threshold_env_var_override` — `monkeypatch.setenv("RATELIMIT_SHARE_SOFT_ALERT_THRESHOLD", "3")` + `get_settings.cache_clear()` + recreate app; member-cookie + 4 POST; assert 3rd POST emits the soft-alert log, 4th does NOT
    - `test_share_redis_outage_allows_creation_with_warning_log` — patch `fake.pipeline` to raise `ConnectionError`; member-cookie + 1 POST `/api/admin/share`; assert returns 201 (fail-soft) AND captured `app.auth.ratelimit` log with `event.action == "ratelimit.redis_unavailable"` AND `labels.scope == "share"` (NOT 429; NOT 500)
  - **Module-surface tests:**
    - `test_ratelimit_module_exports_share_callables` — `from app.core.auth.ratelimit import share_ratelimit_key, share_retry_after_seconds`; assert each is the expected type (functions)
- And `pytest apps/api/tests/test_ratelimit_share_cap.py -v` MUST exit 0 with at least 22 tests green.
- And `pytest apps/api/ -q` MUST exit 0 with NO regressions versus the Story 6.6 baseline (565 tests; this story adds ~22 → expected ~587+).
- And `ruff format apps/api/` + `ruff check apps/api/` MUST pass clean with NO `# noqa` exceptions (repo's strict-clean policy from prior stories).
- And `infra/scripts/check-all.sh` from the repo root MUST exit 0 (all 10 stages green; matches Story 6.6 close-out gate).

**AC-7 — Explicit non-changes: zero frontend / migration / OpenAPI / audit / KNOWN_ENTITY_TYPES / docker-compose drift.**

- And NO frontend changes ride along (the 429 surface is a backend-only contract; the `apps/web/src/api/client.ts` error envelope already surfaces `4xx` responses generically). NO new route in `apps/web/src/routes/`, NO new error-toast keys in `apps/web/src/locales/{en,pl}.json`, NO new visual baselines. Verified by `grep -rn "rate_limited\|share.*cap\|429.*share" apps/web/src` returning ONLY pre-existing Story 6.6 matches (none expected for share).
- And NO Alembic migration is needed (no schema changes — share-cap counter is Redis-only).
- And NO `KNOWN_ENTITY_TYPES` additions are needed in `apps/api/app/core/audit.py` (the rate-limit middleware does NOT call `record_event()` on either the soft-alert path or the hard-fail path). The `app.share.ratelimit.soft_alert` structured log + 429 HTTP behavior + GlitchTip ingest are the binding observability paths (NFR5-OBS-1). Reason for omission: a per-soft-alert audit row would muddy the audit table's purpose (mutation tracking, not observability), and a per-429 audit row would 10× the audit write volume during a share-amplification burst — exactly the condition the cap exists to handle.
- And NO new audit action names are added (do NOT add `share.ratelimit.exceeded` or `share.ratelimit.soft_alert` to the audit vocabulary).
- And the OpenAPI surface DOES NOT change (no new routes; the middleware is invisible to FastAPI's OpenAPI generator). Verified by `pytest apps/api/tests/test_runbook_openapi_consistency.py -v` continuing to pass without modifications. The existing `POST /api/admin/share` route metadata stays exactly as Story 6.5 left it.
- And NO change to the existing CSRF middleware (`apps/api/app/core/auth/csrf.py` stays at its current shape). The share rate-limit middleware coexists with the trio + CSRF independently.
- And NO change to `apps/api/app/core/auth/dependencies.py` (the `current_member_or_admin` dependency stays as Story 6.5 left it — the rate-limit middleware operates BEFORE the dependency resolves).
- And NO change to `apps/api/app/modules/share/admin_router.py` (the route is rate-limited externally by the middleware; the route handler itself is untouched). The Story 6.5 audit emission (`admin.share.create`) continues to fire on every successful 201 response — including the 10th call that ALSO triggers the soft-alert log (the two signals are independent).
- And the existing `infra/scripts/deploy.sh` auto-deploy convention applies: after Story 6.7's dev-commit + Codex review + fix-up (if any) lands on `main`, the next deploy to `.190` MUST include the new share-cap middleware. No new deploy-specific gates needed (the middleware reads `RATELIMIT_SHARE_*` env-vars; if `.190`'s `infra/.env` has none, the defaults apply — `86400s` / `20` / `10` — which match the architecture's binding contract).

## Tasks / Subtasks

- [ ] **T1 — Extend `RateLimitMiddleware` class with `soft_alert_threshold` + `retry_after_seconds_fn` params (AC-1, AC-6)**
  - [ ] T1.1 RED — In `apps/api/tests/test_ratelimit_share_cap.py`, author the 8 class-shape / param-shape tests from AC-6 (`test_middleware_accepts_soft_alert_threshold_kw_only`, `test_middleware_accepts_retry_after_seconds_fn_kw_only`, `test_middleware_backward_compat_no_new_params`, `test_middleware_soft_alert_emits_at_exact_threshold`, `test_middleware_soft_alert_payload_shape`, `test_middleware_soft_alert_does_not_emit_when_disabled`, `test_middleware_retry_after_seconds_fn_takes_precedence`, `test_middleware_retry_after_seconds_fn_default_falls_back_to_window`). Reuse the Story 6.6 `minimal_app_client` fixture pattern (NOT a full `create_app()` — these are class-shape unit tests). Add a parallel `share_caplog` fixture matching the Story 6.6 `ratelimit_caplog` shape but bound to logger name `app.share.ratelimit` (the dedicated `_ListHandler`-on-named-logger pattern from Story 6.6 is the binding precedent — pytest's `caplog` is wiped by `configure_logging` during lifespan startup, so a fresh handler attached to the named logger is the only reliable capture path). Expected initial state: all 8 tests fail with `TypeError` because `RateLimitMiddleware.__init__` doesn't accept the new kwargs.
  - [ ] T1.2 GREEN — In `apps/api/app/core/auth/ratelimit.py`, extend `RateLimitMiddleware.__init__` to accept the two new kw-only params `soft_alert_threshold: int | None = None` and `retry_after_seconds_fn: Callable[[], int] | None = None`. Store on instance. Add `_SHARE_LOG = logging.getLogger("app.share.ratelimit")` module global immediately below the existing `_LOG = logging.getLogger("app.auth.ratelimit")` line (line 33 in current file).
  - [ ] T1.3 GREEN — In `RateLimitMiddleware.__call__`, after the `count = ...` line (line 138) but BEFORE the `if count > self.threshold:` rejection block (line 152), add the soft-alert emission block:
    ```python
    if (
        self.soft_alert_threshold is not None
        and count == self.soft_alert_threshold
    ):
        _SHARE_LOG.warning(
            "share.ratelimit.soft_alert",
            extra={
                "event.action": "share.ratelimit.soft_alert",
                "labels.scope": self.scope_name,
                "labels.key": redis_key,
                "labels.count": count,
                "labels.threshold": self.threshold,
                "labels.soft_alert_threshold": self.soft_alert_threshold,
            },
        )
    ```
  - [ ] T1.4 GREEN — In the rejection block (`if count > self.threshold:`), replace the hardcoded `retry_after_seconds = self.window_seconds` (currently inlined into the JSONResponse body + `Retry-After` header) with:
    ```python
    retry_after_seconds = (
        self.retry_after_seconds_fn()
        if self.retry_after_seconds_fn is not None
        else self.window_seconds
    )
    ```
    And use `retry_after_seconds` in both the body dict (`"retry_after_seconds": retry_after_seconds`) and the header (`"Retry-After": str(retry_after_seconds)`).
  - [ ] T1.5 Run `pytest apps/api/tests/test_ratelimit_share_cap.py -v -k "middleware_accepts or backward_compat or soft_alert_emits or soft_alert_payload or soft_alert_does_not_emit or retry_after_seconds_fn"`. Expected: 8 tests green.
  - [ ] T1.6 Run `pytest apps/api/tests/test_ratelimit_middleware.py -v` — 31 existing Story 6.6 tests still green (regression check: zero-param-change backward compat).

- [ ] **T2 — Author `share_ratelimit_key` + `share_retry_after_seconds` module-top callables (AC-2, AC-3, AC-6)**
  - [ ] T2.1 RED — Author the 8 `share_ratelimit_key` callable tests + 3 `share_retry_after_seconds` tests from AC-6. The `share_ratelimit_key` tests can use a minimal `Request` constructed directly via `Request({"type": "http", "method": "POST", "path": "/api/admin/share", "headers": [...], "query_string": b""})` factory (mirrors the Starlette test idiom) OR via a `MagicMock(spec=Request)` — author's choice. For tests needing JWT cookies, use `encode_token(subject=str(uuid.uuid4()), role="member", secret="test", ttl_minutes=30)` from `app.core.auth.jwt` (Story 6.5 fixture precedent).
  - [ ] T2.2 GREEN — In `apps/api/app/core/auth/ratelimit.py`, add at module-top (BEFORE the existing `_client_ip` helper):
    ```python
    from datetime import UTC, datetime, timedelta

    from app.core.auth.cookies import ACCESS_COOKIE
    from app.core.auth.jwt import TokenError, decode_token
    from app.core.config import get_settings
    ```
    Note: these imports MUST go at the top with the other imports, NOT inline. The `get_settings()` call inside `share_ratelimit_key` MUST be at call time (not module-import time) — `from app.core.config import get_settings` imports the lru_cache-wrapped callable; calling `get_settings()` inside the function body picks up the current cached value.
  - [ ] T2.3 GREEN — Add the `share_ratelimit_key(request: Request) -> str | None` callable per AC-2 binding shape. Place it AFTER the existing `register_ratelimit_key` (line 86-89 currently) in alphabetical order with the trio.
  - [ ] T2.4 GREEN — Add the `share_retry_after_seconds() -> int` callable per AC-3 binding shape. Place it immediately after `share_ratelimit_key` in the same file. Use `datetime.now(UTC)` + `timedelta(days=1)` + `replace(hour=0, ...)` pattern; clamp with `max(..., 1)`.
  - [ ] T2.5 Run `pytest apps/api/tests/test_ratelimit_share_cap.py -v -k "share_key or share_retry_after"`. Expected: 11 tests green (8 share_key + 3 share_retry_after).

- [ ] **T3 — Mount the fourth `RateLimitMiddleware` instance in `main.py:create_app()` (AC-3, AC-6)**
  - [ ] T3.1 RED — Author 4 integration HTTP tests as a smoke check before the full suite: `test_member_first_20_share_creations_return_201`, `test_member_21st_share_creation_returns_429`, `test_admin_21st_share_creation_returns_201`, `test_share_csrf_rejection_does_not_burn_cap`. Use the `test_share_member_permission.py:client` fixture shape verbatim (admin+member seeded + admin+member JWTs + 2 Model rows + fakeredis swap + `X-Portal-Client: web` header). Expected initial state: `test_member_21st...` returns 201 instead of 429 (fourth middleware not yet mounted).
  - [ ] T3.2 GREEN — In `apps/api/app/main.py`, expand the import block (lines 8-13):
    ```python
    from app.core.auth.ratelimit import (
        RateLimitMiddleware,
        login_ratelimit_key,
        refresh_ratelimit_key,
        register_ratelimit_key,
        share_ratelimit_key,
        share_retry_after_seconds,
    )
    ```
  - [ ] T3.3 GREEN — Add the fourth `app.add_middleware(RateLimitMiddleware, ...)` call immediately AFTER the existing register-scope mount (line 102 currently) and BEFORE `install_csrf_middleware(app)` (line 103 currently). Use the AC-3 binding shape verbatim — six kwargs (`scope`, `key_fn`, `window_seconds`, `threshold`, `soft_alert_threshold`, `retry_after_seconds_fn`).
  - [ ] T3.4 Run `pytest apps/api/tests/test_ratelimit_share_cap.py -v -k "first_20 or 21st_share_creation or admin_21st or csrf_rejection_does_not_burn_cap"`. Expected: 4 tests green.
  - [ ] T3.5 Verify CSRF ordering invariant: `pytest apps/api/tests/test_ratelimit_middleware.py::test_login_csrf_rejection_does_not_burn_rate_limit -v` — still green (CSRF still wraps OUTERMOST in the LIFO stack).

- [ ] **T4 — Add three new `Settings` fields + env.example entries (AC-4, AC-6)**
  - [ ] T4.1 RED — Author the 2 env-var-override tests (`test_share_threshold_env_var_override`, `test_share_soft_alert_threshold_env_var_override`). Each MUST `monkeypatch.setenv(...) + get_settings.cache_clear() + recreate app via TestClient(create_app())` (the lru_cache wrapper would otherwise return stale defaults). Expected initial state: `AttributeError` on `settings.ratelimit_share_*` access.
  - [ ] T4.2 GREEN — In `apps/api/app/core/config.py:Settings`, add three new fields (`ratelimit_share_window_seconds: int = 86400`, `ratelimit_share_threshold: int = 20`, `ratelimit_share_soft_alert_threshold: int = 10`) immediately after the existing Story 6.6 ratelimit block (line 48 currently). Add a `# Rate-limiting (Story 6.7, Decision H — per-member share cap)` comment line above the three new fields.
  - [ ] T4.3 GREEN — In `infra/env.example`, append three commented-out reference lines under the existing Story 6.6 ratelimit comments (line 19 currently — append after `# RATELIMIT_REGISTER_THRESHOLD=3`):
    ```
    # RATELIMIT_SHARE_WINDOW_SECONDS=86400
    # RATELIMIT_SHARE_THRESHOLD=20
    # RATELIMIT_SHARE_SOFT_ALERT_THRESHOLD=10
    ```
  - [ ] T4.4 Run `pytest apps/api/tests/test_ratelimit_share_cap.py -v -k "env_var_override"`. Expected: 2 tests green.

- [ ] **T5 — Full integration coverage + observability tests (AC-5, AC-6)**
  - [ ] T5.1 RED — Author the remaining ~12 integration tests from AC-6: `test_member_21st_share_retry_after_within_5s_of_midnight`, `test_member_10th_share_emits_soft_alert_log`, `test_member_9th_share_does_not_emit_soft_alert`, `test_member_11th_share_does_not_emit_soft_alert`, `test_member_get_list_share_returns_403_not_429`, `test_admin_delete_share_not_capped`, `test_anonymous_post_share_returns_401_not_429`, `test_share_per_user_isolation`, `test_share_utc_day_rollover_resets_count`, `test_share_redis_outage_allows_creation_with_warning_log`, `test_ratelimit_module_exports_share_callables`. For the soft-alert log assertions, reuse the `share_caplog` fixture from T1.1 (NOT pytest's built-in `caplog` — see Story 6.6 dev-record + `ratelimit_caplog` precedent). For UTC-day-rollover, monkeypatch `app.core.auth.ratelimit.datetime` to a custom class whose `now(UTC)` returns the desired moment (mirrors Story 6.6 `test_middleware_sliding_window_purges_old_entries` time-monkeypatch pattern). For per-user isolation, the `test_share_member_permission.py:client` fixture seeds ONE member; the new test must seed a SECOND member User row inline and mint a second member-role JWT.
  - [ ] T5.2 GREEN — Iterate on `ratelimit.py` if any test fails. Expected: most tests pass without further code changes; the UTC-rollover test may surface a bug if `datetime.now(UTC)` is captured at module-import time anywhere (should NOT be — both `share_ratelimit_key` and `share_retry_after_seconds` call `datetime.now(UTC)` at function-call time).
  - [ ] T5.3 Run `pytest apps/api/tests/test_ratelimit_share_cap.py -v`. Expected: all 22+ tests green.

- [ ] **T6 — Final quality gate + status flip (all ACs)**
  - [ ] T6.1 Run `pytest apps/api/tests/test_ratelimit_share_cap.py -v` — all 22+ tests green.
  - [ ] T6.2 Run `pytest apps/api/tests/test_ratelimit_middleware.py -v` — 31 Story 6.6 tests still green (zero regression).
  - [ ] T6.3 Run `pytest apps/api/tests/test_share_member_permission.py -v` — 18 Story 6.5 tests still green (no auth/permission drift).
  - [ ] T6.4 Run `pytest apps/api/tests/test_share_admin.py -v` — existing share admin router tests still green (each test makes ≤2 POST calls, well below the 20-threshold).
  - [ ] T6.5 Run `pytest apps/api/tests/test_invite_admin.py test_invite_register.py test_auth*.py -v` — all auth/invite/register tests still green (NO test makes ≥3 register POSTs OR ≥6 login POSTs from the same IP — the existing rate-limits don't bite within a single test).
  - [ ] T6.6 Run `pytest apps/api/ -q` — full backend suite green; expected ~587+ tests (baseline 565 + 22 new).
  - [ ] T6.7 Run `ruff format apps/api/` + `ruff check apps/api/` — clean. No `# noqa` exceptions.
  - [ ] T6.8 Run `infra/scripts/check-all.sh` from repo root — all 10 stages green.
  - [ ] T6.9 Update Dev Agent Record (Agent Model + Debug Log + Completion Notes + File List) below; flip `Status:` to `review`.

## Dev Notes

### Relevant architecture patterns and constraints

- **Decision G — Rate-limit middleware** (`architecture.md` §1553-1579): Story 6.6 implemented the trio (login/refresh/register). Story 6.7 adds the fourth row of the §1568-1573 binding table:

  | Scope | Key | Window | Threshold | Realizes |
  |---|---|---|---|---|
  | `share` | `ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}` | 86400s | 20 creations | FR5-RATELIMIT-2, FR5-MEMBER-3, Decision H |

  Decision G's middleware ordering — "AFTER CSRF check, BEFORE auth dependency resolution" — applies to the share scope too. The share `key_fn` must therefore handle JWT decode + role check LOCALLY (the auth dependency hasn't run yet by the time the middleware fires). Decision G's fail-soft contract (Redis-down → WARNING `app.auth.ratelimit redis_unavailable` + ALLOW) applies verbatim to the share scope; no new fail-soft code path needed.

- **Decision H — Per-member share cap** (`architecture.md` §1581-1592): The architecture binding for this story. Extracted bindings:
  - **Cap key shape:** `ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}` — UTC day boundary, NOT local time (deterministic, no DST math).
  - **Hard threshold:** 20 creations / 24h → HTTP 429 with `Retry-After: <seconds-until-UTC-midnight>` header. Different `Retry-After` semantic from Story 6.6 trio (where `Retry-After = window_seconds` = 60s). This is the binding reason for the new `retry_after_seconds_fn` constructor parameter on `RateLimitMiddleware`.
  - **Soft threshold:** 10 creations / 24h (50% of hard threshold) → structured log `app.share.ratelimit.soft_alert` with payload `{user_id, role, count, threshold, window_end}` on logger `app.share.ratelimit` (NEW logger, distinct from `app.auth.ratelimit` used for the trio's redis_unavailable warning). GlitchTip ingests WARNING-and-above per NFR5-OBS-1.
  - **Admin exemption:** "if `request.state.user.role == Role.admin`, middleware skips both threshold checks for the `share` scope". Repo-specific note: `request.state.user` is NOT populated in this codebase (no middleware sets it; the auth dep returns `uuid.UUID` directly). The architecture pseudocode is a SHAPE not a literal. Implementation: the role check moves into `share_ratelimit_key` (cleanest place — keeps `RateLimitMiddleware` scope-agnostic; the function returns `None` for `admin` role, which short-circuits the middleware before the Redis pipeline). The architecture's "single `if user.role == Role.admin: return await call_next(request)` line" is satisfied by the equivalent `if role == "admin": return None` inside `share_ratelimit_key`.
  - **Scope:** cap applies ONLY to `POST /api/admin/share` (architecture text says `POST /api/share/` but the live router prefix is `/api/admin/share` — see Project Structure Notes drift flag below). `DELETE /api/admin/share/{token}` (admin-only per Decision C) and `GET /api/admin/share` (admin-only list per Decision C) are NOT rate-limited — `share_ratelimit_key` returns `None` for non-POST methods, and the routes are admin-only anyway so the threat model doesn't apply.
  - **Counter survives uvicorn worker restarts:** Redis-backed (architecture says so verbatim). Story 6.6's sliding-window primitive already handles this — Redis is the source of truth; in-process state is zero.

- **Story 6.6 binding precedent — class shape + fail-soft + caplog workaround** (`apps/api/app/core/auth/ratelimit.py` lines 92-165 + `apps/api/tests/test_ratelimit_middleware.py` lines 95-133):
  - Story 6.6's `RateLimitMiddleware` class uses the raw ASGI shape (`async def __call__(self, scope, receive, send)`), NOT the BaseHTTPMiddleware shape (`async def dispatch(self, request, call_next)`). Story 6.7 MUST extend the existing class, NOT swap to BaseHTTPMiddleware. Architecture text "if user.role == Role.admin: return await call_next(request)" implicitly assumes BaseHTTPMiddleware — that text is descriptive, not prescriptive; the binding implementation uses the raw ASGI shape established in 6.6.
  - Story 6.6's fail-soft `try / except (ConnectionError, TimeoutError, OSError):` block catches Redis-down + DNS-fail + connection-pool-exhausted. Story 6.7 inherits this verbatim (no change needed — the share scope reuses the same Redis pipeline path). The `test_share_redis_outage_allows_creation_with_warning_log` test verifies the share scope inherits the fail-soft behavior.
  - Story 6.6's `ratelimit_caplog` fixture (lines 95-133) attaches a `_ListHandler` directly to logger `app.auth.ratelimit`. Pattern repeats verbatim for Story 6.7's `share_caplog` fixture — same `_ListHandler`, bound to logger `app.share.ratelimit`. Reason (per Story 6.6 dev record): `app.core.logging.configure_logging` does `root.handlers[:] = [...]` during FastAPI lifespan startup, wiping pytest's `caplog` handler; a fresh handler attached to the named logger sidesteps the wipe. Story 6.7 inherits the same workaround.

- **Story 6.5 binding precedent — share-router permission expansion + test fixture shape** (`apps/api/app/modules/share/admin_router.py` lines 25-31 + `apps/api/tests/test_share_member_permission.py` lines 39-99):
  - The `POST /api/admin/share` route currently uses `current_member_or_admin` (Story 6.5 swap from `current_admin`). Story 6.7 does NOT change this — the dependency resolution still fires AFTER the rate-limit middleware. The middleware's job is to count and cap; the dependency's job is to authenticate and authorize. The two are independent.
  - `test_share_member_permission.py:client` is the binding fixture shape for Story 6.7 integration tests. The fixture seeds: (a) admin User from `seed_admin()`; (b) one member User row inline; (c) two Model rows; (d) mints admin-role + member-role JWTs via `encode_token(subject=..., role="admin"|"member", secret="test", ttl_minutes=30)`; (e) sets `X-Portal-Client: web` on TestClient headers; (f) swaps `app.state.redis` to a fakeredis MagicMock factory. Story 6.7's `client` fixture extends this with ONE additional member User row (for the per-user-isolation test) AND the `share_caplog` fixture composed as a co-yielded handler.

- **DOC-DRIFT (Project Structure Notes flag — for `bmad-correct-course` post-Story 6.7):**
  1. Architecture.md §1589 + epics.md §1631 both write `POST /api/share/` and `DELETE /api/share/{id}`. The live router prefix at `apps/api/app/modules/share/admin_router.py:18` is `/api/admin/share`. Story 6.5 already flagged this drift (sprint-status entry for 6-5). Story 6.7 uses the correct live path verbatim. The drift survives — `bmad-correct-course` to align epics.md + architecture.md text to `/api/admin/share` remains pending.
  2. Architecture.md §1588 + §1592 pseudocode "`if user.role == Role.admin: return await call_next(request)` line in `apps/api/app/core/auth/ratelimit.py`" assumes BaseHTTPMiddleware shape. The live class uses raw ASGI shape. Story 6.7 implementation expresses the exemption via `share_ratelimit_key` returning `None` for admin — semantically equivalent, structurally different from the architecture pseudocode.
  3. Architecture.md §1587 names the structured log as `app.share.ratelimit.soft_alert`. Story 6.7 decomposes this as logger=`app.share.ratelimit` + event.action=`share.ratelimit.soft_alert` (mirrors Story 6.6's `event.action="ratelimit.redis_unavailable"` decomposition). Both interpretations satisfy NFR5-OBS-1; the decomposition is the binding for Story 6.7.

### Implementation skeleton — `apps/api/app/core/auth/ratelimit.py` patch (binding for shape)

```diff
 import logging
 import time
 import uuid
 from collections.abc import Callable
+from datetime import UTC, datetime, timedelta
 from typing import TYPE_CHECKING

 import redis.exceptions
 from fastapi import Request
 from fastapi.responses import JSONResponse

+from app.core.auth.cookies import ACCESS_COOKIE
+from app.core.auth.jwt import TokenError, decode_token
+from app.core.config import get_settings
+
 if TYPE_CHECKING:
     from starlette.types import ASGIApp, Receive, Scope, Send

 _LOG = logging.getLogger("app.auth.ratelimit")
+_SHARE_LOG = logging.getLogger("app.share.ratelimit")
```

```diff
 def register_ratelimit_key(request: Request) -> str | None:
     if request.method == "POST" and request.url.path == "/api/auth/register":
         return f"ip:{_client_ip(request)}"
     return None


+def share_ratelimit_key(request: Request) -> str | None:
+    """Per-member daily share-creation key + admin exemption.
+
+    Returns None for any non-POST / non-/api/admin/share request, missing or
+    invalid JWT, admin role (Decision H exemption), or non-member/non-admin
+    roles (auth dependency will reject with 403). Returns
+    ``user:{user_id}:day:{YYYY-MM-DD}`` for valid member requests so the
+    middleware's full Redis key is ``ratelimit:share:user:{...}:day:{...}``.
+    """
+    if request.method != "POST" or request.url.path != "/api/admin/share":
+        return None
+    token = request.cookies.get(ACCESS_COOKIE)
+    if not token:
+        return None
+    try:
+        claims = decode_token(token, secret=get_settings().jwt_secret)
+    except TokenError:
+        return None
+    role = claims.get("role")
+    if role == "admin":
+        return None  # Decision H admin exemption
+    if role != "member":
+        return None  # agent / unknown → let auth dep return 403
+    user_id = claims.get("sub")
+    if not user_id:
+        return None
+    today_utc = datetime.now(UTC).strftime("%Y-%m-%d")
+    return f"user:{user_id}:day:{today_utc}"
+
+
+def share_retry_after_seconds() -> int:
+    """Seconds remaining until the next UTC midnight (next day boundary)."""
+    now = datetime.now(UTC)
+    tomorrow = (now + timedelta(days=1)).replace(
+        hour=0, minute=0, second=0, microsecond=0
+    )
+    return max(int((tomorrow - now).total_seconds()), 1)
+
+
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
+        soft_alert_threshold: int | None = None,
+        retry_after_seconds_fn: Callable[[], int] | None = None,
     ) -> None:
         self.app = app
         self.scope_name = scope
         self.key_fn = key_fn
         self.window_seconds = window_seconds
         self.threshold = threshold
+        self.soft_alert_threshold = soft_alert_threshold
+        self.retry_after_seconds_fn = retry_after_seconds_fn
```

```diff
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

+        if (
+            self.soft_alert_threshold is not None
+            and count == self.soft_alert_threshold
+        ):
+            _SHARE_LOG.warning(
+                "share.ratelimit.soft_alert",
+                extra={
+                    "event.action": "share.ratelimit.soft_alert",
+                    "labels.scope": self.scope_name,
+                    "labels.key": redis_key,
+                    "labels.count": count,
+                    "labels.threshold": self.threshold,
+                    "labels.soft_alert_threshold": self.soft_alert_threshold,
+                },
+            )
+
         if count > self.threshold:
+            retry_after_seconds = (
+                self.retry_after_seconds_fn()
+                if self.retry_after_seconds_fn is not None
+                else self.window_seconds
+            )
             response = JSONResponse(
                 {
                     "detail": "rate_limited",
                     "scope": self.scope_name,
-                    "retry_after_seconds": self.window_seconds,
+                    "retry_after_seconds": retry_after_seconds,
                 },
                 status_code=429,
-                headers={"Retry-After": str(self.window_seconds)},
+                headers={"Retry-After": str(retry_after_seconds)},
             )
             await response(scope, receive, send)
             return

         await self.app(scope, receive, send)
```

### Implementation skeleton — `apps/api/app/main.py` patch (binding for shape)

```diff
 from app.core.auth.ratelimit import (
     RateLimitMiddleware,
     login_ratelimit_key,
     refresh_ratelimit_key,
     register_ratelimit_key,
+    share_ratelimit_key,
+    share_retry_after_seconds,
 )
```

```diff
     app.add_middleware(
         RateLimitMiddleware,
         scope="register",
         key_fn=register_ratelimit_key,
         window_seconds=settings.ratelimit_register_window_seconds,
         threshold=settings.ratelimit_register_threshold,
     )
+    # Story 6.7: per-member share-token cap (Decision H). Reuses the Story 6.6
+    # middleware class with two new optional params for soft-alert + dynamic
+    # Retry-After. Admin exemption + JWT-cookie role check live inside
+    # share_ratelimit_key (returns None for admin / anon / non-member roles,
+    # short-circuiting the Redis pipeline). Scope: POST /api/admin/share only;
+    # DELETE + GET on the same prefix are method-filtered out by the key_fn.
+    app.add_middleware(
+        RateLimitMiddleware,
+        scope="share",
+        key_fn=share_ratelimit_key,
+        window_seconds=settings.ratelimit_share_window_seconds,
+        threshold=settings.ratelimit_share_threshold,
+        soft_alert_threshold=settings.ratelimit_share_soft_alert_threshold,
+        retry_after_seconds_fn=share_retry_after_seconds,
+    )
     install_csrf_middleware(app)
```

### Implementation skeleton — `apps/api/app/core/config.py` patch

```diff
     # Rate-limiting (Story 6.6, Decision G)
     ratelimit_login_window_seconds: int = 60
     ratelimit_login_threshold: int = 5
     ratelimit_refresh_window_seconds: int = 60
     ratelimit_refresh_threshold: int = 10
     ratelimit_register_window_seconds: int = 60
     ratelimit_register_threshold: int = 3
+    # Rate-limiting (Story 6.7, Decision H — per-member share cap)
+    ratelimit_share_window_seconds: int = 86400
+    ratelimit_share_threshold: int = 20
+    ratelimit_share_soft_alert_threshold: int = 10
```

### Implementation skeleton — `infra/env.example` patch

```diff
 # RATELIMIT_REGISTER_WINDOW_SECONDS=60
 # RATELIMIT_REGISTER_THRESHOLD=3
+# RATELIMIT_SHARE_WINDOW_SECONDS=86400
+# RATELIMIT_SHARE_THRESHOLD=20
+# RATELIMIT_SHARE_SOFT_ALERT_THRESHOLD=10
```

### Implementation skeleton — `apps/api/tests/test_ratelimit_share_cap.py` (binding for shape)

```python
"""Tests for the Initiative 5 per-member share-token cap (Story 6.7).

Covers AC-1 through AC-7 from the Story 6.7 spec:
- AC-1: RateLimitMiddleware class extension (soft_alert_threshold + retry_after_seconds_fn)
- AC-2: share_ratelimit_key callable (path + JWT + admin exemption + member key shape)
- AC-3: Fourth middleware instance mounted in main.py with CSRF-OUTERMOST ordering preserved
- AC-4: Three new Settings fields with env-var tunability
- AC-5: HTTP-layer threshold verification (10th soft-alert + 21st hard-fail + admin exempt)
- AC-6: Per-user isolation + UTC-day rollover + Retry-After-to-midnight
- AC-7: Zero frontend / migration / OpenAPI / audit / KNOWN_ENTITY_TYPES drift

Three fixture rigs:
- ``minimal_app_client`` — fresh FastAPI() with /test-route, used for class-shape
  unit tests of the extended RateLimitMiddleware params.
- ``share_client`` — TestClient(create_app()) + fakeredis swap + seeded admin
  + TWO seeded members + admin-token + two member-tokens (A and B) + two Model
  rows; mirrors test_share_member_permission.py:client fixture verbatim.
- ``share_caplog`` — _ListHandler attached to logger ``app.share.ratelimit``
  (mirrors test_ratelimit_middleware.py:ratelimit_caplog precedent because
  pytest's built-in caplog gets wiped by configure_logging at lifespan startup).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import fakeredis
import fakeredis.aioredis
import pytest
import redis.exceptions
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.auth.ratelimit import (
    RateLimitMiddleware,
    share_ratelimit_key,
    share_retry_after_seconds,
)
from app.core.db.models import Category, Model, User, UserRole
from app.core.db.session import get_engine
from app.main import create_app


# ---------- Fixtures (full bodies authored in T1.1 + T3.1) ----------

@pytest.fixture
def minimal_app_client():
    """Construct a fresh minimal FastAPI() per call with parameterized middleware kwargs."""
    ...  # see Story 6.6 test_ratelimit_middleware.py:minimal_app_client for the binding precedent

@pytest.fixture
def share_caplog():
    """_ListHandler attached to logger ``app.share.ratelimit`` (mirrors Story 6.6 pattern)."""
    ...  # see Story 6.6 test_ratelimit_middleware.py:ratelimit_caplog lines 109-133

@pytest.fixture
def share_client(tmp_path, monkeypatch):
    """Full create_app() + admin + two seeded members + tokens + fakeredis swap."""
    ...  # extend test_share_member_permission.py:client with a SECOND member seed


# ---------- AC-1 class-shape tests ----------

def test_middleware_accepts_soft_alert_threshold_kw_only(minimal_app_client):
    c, _ = minimal_app_client(
        scope="x", key_fn=lambda r: "k", window_seconds=60, threshold=20, soft_alert_threshold=10
    )
    # Access via the registered middleware factory in the Starlette stack.
    ...

def test_middleware_backward_compat_no_new_params(minimal_app_client):
    c, _ = minimal_app_client(scope="x", key_fn=lambda r: "k", threshold=5)
    # 6.6 trio construction shape — verify no AttributeError / TypeError.
    ...

def test_middleware_soft_alert_emits_at_exact_threshold(minimal_app_client, share_caplog):
    c, _ = minimal_app_client(
        scope="x", key_fn=lambda r: "k", window_seconds=60, threshold=20, soft_alert_threshold=10
    )
    for i in range(1, 11):
        r = c.post("/test-route")
        assert r.status_code == 200, f"call {i} unexpectedly rejected"
    # The 10th call MUST have emitted the soft-alert; the 9th must NOT have.
    soft_records = [
        rec for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert len(soft_records) == 1
    assert soft_records[0].__dict__["labels.count"] == 10

# ... (remaining tests per AC-6 binding list)
```

### Previous story intelligence (Story 6.6 dev record — bindings for Story 6.7)

- **`ZADD` member uniqueness — keep the `f"{now_ms}-{uuid.uuid4().hex}"` shape verbatim.** Story 6.6 dev record discovered the literal architecture pseudocode `ZADD key now now` would collapse sub-millisecond bursts into one entry (same score + same member = no-op ZADD). Story 6.7 inherits the fix — `ZADD key {f"{now_ms}-{uuid4().hex}": now_ms}` — no change needed (the share scope reuses the same `__call__` body). The architecture pseudocode at §1561 (`ZADD ratelimit:{scope}:{key} now now`) remains drift relative to live code; bmad-correct-course flag carries over from 6.6 retro.
- **CSRF ordering inversion — keep the existing main.py install pattern.** Story 6.6 dev record discovered that Story 6.6 spec's literal "AFTER `install_csrf_middleware`" placement makes rate-limit OUTERMOST (wrong — CSRF must wrap outermost so a 403 csrf_required doesn't burn rate-limit budget). The live code inverts: rate-limit `add_middleware` × N → `install_csrf_middleware` LAST. Story 6.7 inserts the fourth `add_middleware(share)` call into the trio block (BEFORE the CSRF install) — preserves the CSRF-OUTERMOST invariant.
- **`@app.middleware("http")` decorator vs `add_middleware` LIFO — Starlette behavior is identical.** Story 6.6 dev record clarified that Starlette's `BaseHTTPMiddleware` registered via `@app.middleware("http")` decorator is functionally equivalent to `add_middleware` — both prepend to `user_middleware`. The architecture-text claim about decorator wrapping OUTERMOST is wrong (Dev Notes drift). Story 6.7 has no decorator-vs-method ambiguity; uses `add_middleware` exclusively.
- **caplog handler wipe at lifespan startup — `_ListHandler` on the named logger.** Story 6.6's `ratelimit_caplog` fixture (lines 95-133 in `test_ratelimit_middleware.py`) attaches a `_ListHandler` directly to the named logger because `configure_logging` does `root.handlers[:] = [...]` during FastAPI lifespan startup, wiping pytest's built-in `caplog` handler. Story 6.7 MUST repeat the pattern verbatim for the new `app.share.ratelimit` logger; the binding fixture name is `share_caplog`.
- **`monkeypatch.setenv + get_settings.cache_clear() + recreate app` for env-var tunability tests.** Story 6.6 dev record shows the only reliable way to exercise env-var overrides is monkeypatch env BEFORE `get_settings.cache_clear()` BEFORE `create_app()` (the lru_cache wrapper otherwise returns stale defaults; the middleware reads settings at app-construction time, NOT per-request). Story 6.7 inherits the pattern verbatim for `RATELIMIT_SHARE_*` overrides.
- **Existing test isolation OK — no per-test thresholds bite.** Story 6.6 dev record confirms `pytest apps/api/tests/test_auth*.py + test_invite_register.py` all keep their per-test login/refresh/register call counts ≤2, well below the trio thresholds (5/10/3 respectively). Story 6.7's threshold-20 share cap is even looser; the existing `test_share_member_permission.py` happy-path test makes ONE POST and the regression tests at most 1-2 — no rate-limit interaction.

### Project Structure Notes

- **Alignment with unified project structure:** `apps/api/app/core/auth/ratelimit.py` is the canonical module location per Decision G (matches Story 6.6 placement). `apps/api/tests/test_ratelimit_share_cap.py` is a NEW sibling to `test_ratelimit_middleware.py` (NOT extending the existing file — the share-scope test rig has different fixture needs: seeded member + admin User rows + JWT cookies + Model rows for the route to succeed; keeping the rigs separate keeps both test files readable). `apps/api/app/core/config.py` rate-limiting block extends in-place (single `# Rate-limiting` section spans both 6.6 + 6.7 bindings).
- **DOC-DRIFT flags (carry over to bmad-correct-course post-Story 6.7):**
  1. Architecture.md §1589 + epics.md §1631 path `POST /api/share/` vs live router `/api/admin/share` (Story 6.5 carry-over).
  2. Architecture.md §1588 BaseHTTPMiddleware pseudocode (`call_next`) vs live raw-ASGI shape — semantic equivalence noted; recommend tightening architecture text to "(shape; implemented as `share_ratelimit_key` returning `None` for admin)".
  3. Architecture.md §1587 structured log name `app.share.ratelimit.soft_alert` decomposed as logger=`app.share.ratelimit` + event=`share.ratelimit.soft_alert` — recommend tightening architecture text.
  4. Architecture.md §1561 + §1565 `ZADD score=now member=now` collision — Story 6.6 retro carry-over.
- **No conflict with unified structure:** all changes stay within the existing auth-foundational module family (`core/auth/ratelimit.py`), existing config module (`core/config.py`), existing app factory (`main.py`), existing test directory (`apps/api/tests/`). NO new package directories, NO sub-module additions.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision G — Rate-limit middleware (Redis sliding-window, key shape, threshold config, middleware placement)] — algorithm + key shape + threshold sourcing + middleware placement (§1553-1579).
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision H — Per-member share cap (cap key shape, soft/hard thresholds, admin exemption)] — cap key + soft/hard thresholds + admin exemption + scope binding (§1581-1592).
- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.7 — Per-member share-token cap (extension of 6.6 middleware to `share` scope + soft-alert)] — acceptance check shape (§1627-1635).
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-MEMBER-3] — per-member rate-limit + daily volume cap (≤20/day hard, 50% soft-alert) (line 1182).
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-RATELIMIT-2] — per-member share-token creation cap in the same middleware family (line 1205).
- [Source: _bmad-output/planning-artifacts/prd.md#NFR5-SEC-3] — audit scenario coverage (line 1221; share-link amplification scenario verifies Story 6.7 output).
- [Source: _bmad-output/implementation-artifacts/6-6-ratelimit-middleware-login-refresh-register.md] — Story 6.6 binding precedent (class shape, fail-soft, caplog workaround, CSRF ordering inversion, ZADD member shape).
- [Source: _bmad-output/implementation-artifacts/6-5-member-permission-expansion-share-router.md] — Story 6.5 binding precedent (member permission expansion to `POST /api/admin/share`, fixture shape, JWT minting).
- [Source: apps/api/app/core/auth/ratelimit.py:1-166] — live Story 6.6 module (extend in place).
- [Source: apps/api/app/main.py:8-103] — live Story 6.6 middleware install sequence (insert fourth `add_middleware` between trio and `install_csrf_middleware`).
- [Source: apps/api/app/core/config.py:42-48] — live Story 6.6 ratelimit Settings block (extend with three new fields).
- [Source: apps/api/app/modules/share/admin_router.py:18-54] — live share router (no change; rate-limit applies externally).
- [Source: apps/api/app/core/auth/dependencies.py:13,46-53,69-78] — `_MEMBER_OR_ADMIN_ROLES` + `current_member_or_admin` dependency (no change).
- [Source: apps/api/app/core/auth/jwt.py:24-28] — `decode_token` + `TokenError` (used inside `share_ratelimit_key`).
- [Source: apps/api/app/core/auth/cookies.py:7] — `ACCESS_COOKIE = "portal_access"` constant.
- [Source: apps/api/tests/test_ratelimit_middleware.py:95-162] — Story 6.6 `_ListHandler` + `ratelimit_caplog` + `integration_client` fixture precedents.
- [Source: apps/api/tests/test_share_member_permission.py:39-99] — Story 6.5 `client` fixture (binding shape for `share_client` with TWO members).
- [Source: infra/env.example:14-19] — Story 6.6 commented-out RATELIMIT_*_* env-var examples (extend with three new RATELIMIT_SHARE_* lines).

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
