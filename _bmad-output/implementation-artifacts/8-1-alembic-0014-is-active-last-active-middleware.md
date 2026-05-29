# Story 8.1: Alembic `0014_users_is_active_last_active` + `LastActiveMiddleware` + Epic 8 systemic-gate bundle

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer (Ezop, banking-IT operator wearing the dev-team ITCM hat),
I want **the database schema, request-side throttle middleware, and the cross-story tooling/process bundle that Epic 8 needs as its foundation** shipped as a single low-risk story, namely:

1. **Alembic migration `0014_users_is_active_last_active.py`** that adds two new columns to the `user` table — `is_active BOOLEAN NOT NULL DEFAULT TRUE` (existing `admin` + `agent` + any seeded `member` rows backfill to `TRUE` so the migration is a null-op for live data) and `last_active_at DATETIME NULL` (populated only by the middleware shipped in this same story; default `NULL` for all backfilled rows). Singular table name `user` per the Init 0 convention codified in `apps/api/app/core/db/models/_user.py:21` (`__tablename__ = "user"`). The migration chains `0013_users_2fa_columns` → `0014_users_is_active_last_active` and `downgrade()` is strict LIFO (`drop_column("last_active_at")` then `drop_column("is_active")`).
2. **`LastActiveMiddleware`** in NEW `apps/api/app/core/auth/middleware.py` per Decision I (architecture.md §1601-1630) — implements the **`SET NX EX 300`** atomic Redis-throttled `UPDATE user SET last_active_at = NOW()` write path that gates DB writes to ≤1/5min/user regardless of authenticated request rate (NFR5-PERF-1 verbatim). The middleware MUST be Redis-down fail-soft (same shape as `RateLimitMiddleware` at `apps/api/app/core/auth/ratelimit.py:215-227` — log `LOG.warning("last_active.redis_unavailable", ...)` and pass the request through; never 5xx because Redis hiccupped); MUST be a no-op for unauthenticated requests (decoded JWT yields no user → pass through with no DB hit); MUST be wired into `apps/api/app/main.py:create_app()` LIFO-after the rate-limit + CSRF middleware install block so the execution order is (outermost-to-innermost) CSRF → rate-limit trio → last-active → handler.
3. **`User.last_active_at` + `User.is_active` SQLModel fields** in `apps/api/app/core/db/models/_user.py` mirroring the Story 7.1 precedent for `totp_secret` + `totp_enabled_at` (the `UTCDateTime` decorator from `_helpers.py` for the timestamp field; plain `bool` with `default=True` for the active flag).
4. **`audit.py` `user` entity_type comment block extended** with the 6 Epic 8-class action names that future stories 8.3 + 8.4 + 8.5 will emit (`user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`, `auth.password.reset.initiated`, `auth.password.reset.completed`). NO new entry in `KNOWN_ENTITY_TYPES` (the existing `user` entity_type covers all 6); this is a docstring-registry update only that ships the FR5-AUDIT-1 (E8 subset) action-name registration ahead of the emitter stories so the comment block reflects the planned vocabulary before any caller goes red.
5. **Three new `check-all.sh` systemic gates** bundled into this story's chore commit per Epic 7 retro action items §1 + §2 (epic-7-retro-2026-05-20.md:201-211) — these are the three carry-over gates whose absence cost Story 7.1 a production incident and that should have landed before Story 7.2 ran but slipped to Story 8.1 by epic-retro consensus:
   1. **Settings/env.example/docker-compose.yml diff stage** — script asserts every `Settings` field name maps 1:1 to an `infra/env.example` line (uppercase snake) AND every `infra/env.example` non-comment line maps to a `services.api.environment` (or `services.arq-worker.environment`) entry in `infra/docker-compose.yml`. Tri-directional check catches dropped-on-the-floor env-var wiring (the Story 6.4 / 6.6 / 6.7 / 7.1 recurrent regression class).
   2. **`uv lock --check` stage** — runs in `apps/api/` then in `workers/render/` to assert the lockfile is up-to-date with `pyproject.toml`. Catches the Story 7.1 stale-lockfile class.
   3. **`infra/.env` secret-provisioning verification stage** (LOCAL-only — the dev-box `infra/.env` file, NOT `.190`; per `feedback_local_only_docs.md` we don't reach into `.190` from `check-all.sh`) — scans `infra/env.example` for `^[A-Z_]+=$` patterns (empty-on-purpose secret slots), then for each one asserts the same name exists in `infra/.env` with a non-empty value. NEW failure mode: a missing secret slot in local `.env` fails this stage; the matching pre-deploy assertion against `.190` `infra/.env` lands in Story 9.x or 10.x as a `deploy.sh` enhancement, NOT here.
6. **Promote the per-file `client` test fixture** to `apps/api/tests/conftest.py` per Epic 6 retro item §4 + Epic 7 retro item §6 (saturation threshold reached at ~10 files — `test_2fa_enrollment.py`, `test_2fa_verify.py`, `test_2fa_regenerate.py`, `test_2fa_disable.py`, `test_enforce_2fa_login.py`, `test_invite_admin.py`, `test_invite_register.py`, `test_share_admin.py`, `test_share_service.py`, `test_admin_audit.py`). The fixture lives in conftest as a NEW `@pytest.fixture` that mirrors the `test_2fa_enrollment.py:50-74` shape (fresh app + tmpdir SQLite + fakeredis swap onto `app.state.redis`); existing per-file fixtures are NOT removed in this story (mass refactor is out-of-scope and would balloon the diff — they remain in place as duplicate definitions, harmless because pytest resolves the local one preferentially over conftest). NEW test files in Epic 8 (8.2-8.6) use the conftest fixture directly.
7. **Story-local backend tests for the middleware throttle invariant** — the binding NFR5-PERF-1 verification: a scripted test inserts a seeded user, mounts the app with a real fakeredis, fires 50 authenticated GET requests within 60 seconds of wall time (using `freezegun` or `time.time` monkeypatched in tight succession) and asserts EXACTLY 1 `UPDATE user SET last_active_at` SQL statement was executed against the test DB (captured via SQLAlchemy `Engine` event listener attached at fixture scope), plus the corresponding column value in the DB is the SINGLE timestamp from the first request (subsequent requests hit the Redis `SET NX` path and are throttled out). A second test variant fast-forwards >300s between two batches and asserts EXACTLY 2 updates (one per batch). A third test variant verifies anonymous (no JWT cookie) requests produce ZERO updates regardless of count.
8. **Opportunistic ride-along: `auth.login.success` X-Request-ID propagation patch** per Epic 7 retro action item §8 (one-line touch: thread `request.headers.get("x-request-id")` into the `record_event(request_id=...)` argument at the single-factor `POST /api/auth/login` emission site in `apps/api/app/modules/auth/router.py`). Only the single-factor login path needs patching; the partial-auth + TOTP-verify path already emits via `verify_second_factor` which threads it correctly (verified per epic-7-retro line 47). Verifiable: a new test asserts `audit_log.request_id == "test-correlation-uuid-abc"` when the login request carries `X-Request-ID: test-correlation-uuid-abc`.
9. **Opportunistic ride-along: TOTP_FERNET_KEY rotation triage entry** per Epic 7 retro action item §10 — add ONE entry to `_bmad-output/triage-backlog.md` reminding to author a key-rotation runbook (estimated trigger date 2027-05-20 = +12 months from Epic 7 close at 2026-05-20). Single block per the file's existing entry format (no new section).

so that:

- **Epic 8 has its load-bearing schema + middleware foundation** — Stories 8.2 (admin Users tab) and 8.3 (per-user actions) cannot ship without the `is_active` + `last_active_at` columns existing on disk AND `last_active_at` being populated by something. Story 8.1 unblocks the entire admin-panel chain.
- **NFR5-PERF-1 is realized** with a verifiable invariant — 50 requests → 1 UPDATE is the binding test shape that survives into the Epic 9 audit; the `SET NX EX 300` primitive matches Decision I §1611-1619 verbatim (no in-memory throttle, no ZADD heatmap, no cron batch).
- **The Epic 7 retro carry-over tooling debt closes in one chore commit** rather than re-piling story-by-story. The next 5 stories (8.2-8.6) inherit a `check-all.sh` that catches the Story 7.1 incident class structurally instead of via per-story AC enforcement. The conftest fixture promotion stops the "every new test file copy-pastes 25 lines of `client` boilerplate" trend.
- **The audit vocabulary is documented before emission**, which means the future Story 8.3 + 8.4 + 8.5 implementers (which may run autonomously per `feedback_itcm_autonomous_mode.md`) discover the action-name list from `audit.py` itself rather than re-deriving it from epics.md, preventing the doc-drift class that surfaced in Epic 7 (8 unresolved items at retro time).
- **The runtime behavior change for `is_active` (login + refresh check) stays in Story 8.3** — Story 8.1 ships the column with `DEFAULT TRUE` backfill so live traffic is unaffected; the `is_active = FALSE` enforcement at `POST /api/auth/login` + `POST /api/auth/refresh` is part of 8.3's PATCH-deactivation flow per epics §1786 verbatim. **Critical scope boundary:** Story 8.1 MUST NOT modify `apps/api/app/modules/auth/router.py:login()` or `apps/api/app/modules/auth/router.py:refresh()` for is_active enforcement (only the X-Request-ID patch on the single-factor login emission, which is orthogonal). Wiring is_active into the login/refresh path in 8.1 would split the is_active runtime story across two PRs and is explicitly forbidden by the epics §1786 ownership boundary.

### Story scope is strictly bounded

- **NEW files (5):**
  - `apps/api/migrations/versions/0014_users_is_active_last_active.py`
  - `apps/api/app/core/auth/middleware.py`
  - `apps/api/tests/test_migration_0014.py`
  - `apps/api/tests/test_last_active_middleware.py`
  - (no new web/worker files — pure backend + infra)
- **MODIFIED files (~10):**
  - `apps/api/app/core/db/models/_user.py` (add 2 fields)
  - `apps/api/app/main.py` (register middleware in `create_app()` LIFO-after CSRF block)
  - `apps/api/app/core/audit.py` (extend `user` entry comment block with 6 E8 action names)
  - `apps/api/app/modules/auth/router.py` (one-line X-Request-ID thread on single-factor `auth.login.success`)
  - `apps/api/tests/conftest.py` (add `client` fixture; do NOT modify existing tests)
  - `apps/api/tests/test_audit.py` (verify the docstring update if it's covered by a comment-parsing test; otherwise leave unchanged)
  - `infra/scripts/check-all.sh` (3 new stages, fast-to-slow ordering preserved)
  - `_bmad-output/triage-backlog.md` (1 new entry, TOTP_FERNET_KEY rotation)
- **STRICTLY OUT OF SCOPE** (these belong to later stories and adding them here splits ownership / inflates the diff):
  - `POST /api/admin/users/...` endpoint — Story 8.3.
  - `is_active` check at `POST /api/auth/login` + `POST /api/auth/refresh` — Story 8.3 per epics §1786.
  - `users.force_2fa_enrollment` column — Story 8.4 (optional new column per epics §1798; implementer's call at 8.4 time, NOT preemptively here).
  - Admin Users tab UI (`apps/web/src/modules/admin/UsersPage.tsx`) — Story 8.2.
  - Any frontend / vitest / Playwright change — Epic 8 web work starts at 8.2.
  - Pre-deploy `.190` secret verification stage — defer to `deploy.sh` enhancement in Story 9.x or 10.x.
  - Mass refactor of per-file `client` fixtures to USE the conftest fixture — opportunistic during 8.2-8.6 dev only; this story PROMOTES the fixture, doesn't migrate every caller.
  - `docs/concurrency-patterns.md` — separate Epic 7 retro action item (§7); recommended before Story 8.4, NOT a Story 8.1 deliverable.
  - `bmad-correct-course` Decision-E / Decision-F doc-drift patches — separate retro item (§4 + §5); recommended before Story 8.4, NOT bundled here.

No new dependencies (no `freezegun` required if `time.time` monkeypatch suffices in tests). No new audit action emissions (the 6 names are documented but not yet emitted — emissions ship in 8.3-8.5). No new entity_type. No new Settings field. No new rate-limit scope. No new env-var (the `check-all.sh` enhancements consume existing surfaces). No new alembic dependency beyond the chained revision.

## Acceptance Criteria

**AC-1 — Alembic migration `0014_users_is_active_last_active.py` adds two columns to the `user` table with binding shape; round-trip clean.**

- Given the head migration is `0013_users_2fa_columns` (verified via `alembic heads` against `apps/api/alembic.ini`),
- When Story 8.1 ships,
- Then `apps/api/migrations/versions/0014_users_is_active_last_active.py` MUST exist as a NEW file with:
  - `revision = "0014_users_is_active_last_active"`
  - `down_revision = "0013_users_2fa_columns"`
  - `branch_labels = None`, `depends_on = None`
  - A module-level docstring (lines 1-N before `from __future__`) explaining Decision I context, mirroring the `0013_users_2fa_columns.py:1-31` precedent shape (3-4 paragraphs: realizes-which-FR/NFR; column shape rationale; why this story includes both columns in one migration; why no new table).
  - `upgrade()` adds `user.is_active BOOLEAN NOT NULL DEFAULT TRUE` (server-side default ensures existing rows backfill atomically — the migration uses `sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"))` for the SQLite-flavored boolean true; on Postgres the same `server_default=sa.text("TRUE")` works — verify via the round-trip test against SQLite which is the only target dialect today per Init 0).
  - `upgrade()` adds `user.last_active_at DATETIME NULL` (no server default; `nullable=True`).
  - `downgrade()` is strict LIFO: `op.drop_column("user", "last_active_at")` then `op.drop_column("user", "is_active")`.
- And the round-trip test `test_migration_0014_round_trip` in NEW `apps/api/tests/test_migration_0014.py` MUST execute `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` and assert:
  - After first upgrade: `PRAGMA table_info(user)` includes columns `is_active` (notnull=1, default=`1`) AND `last_active_at` (notnull=0, default=NULL).
  - After downgrade: neither column is in `PRAGMA table_info(user)`; the `0013_users_2fa_columns` columns (`totp_secret`, `totp_enabled_at`) are still present.
  - After second upgrade: state matches the post-first-upgrade snapshot (idempotent forward).
- And the round-trip test reuses the `_round_trip_db` fixture pattern from `apps/api/tests/test_migration_0012.py:38-58` verbatim (the `DATABASE_URL` env-var override + `get_settings.cache_clear()` + `get_engine.cache_clear()` discipline is binding because alembic env.py reads from `get_settings().database_url`; bypassing this fixture pattern is the recurring "tests touch the session DB" anti-pattern).
- And the binding NFR5-INT-1 invariant is preserved: the existing `admin` + `agent` rows that `seed_admin()` writes during app startup MUST NOT need a backfill (the `DEFAULT TRUE` on `is_active` covers them at upgrade time; `last_active_at` stays NULL until the middleware writes it — no agent-service-account regression).

**AC-2 — `User` SQLModel gains two fields matching the migration column shape exactly.**

- Given the User SQLModel at `apps/api/app/core/db/models/_user.py:20-40`,
- When Story 8.1 ships,
- Then the class MUST have:
  - `is_active: bool = Field(default=True)` (matches the migration's `nullable=False DEFAULT TRUE`; default=True so `User(...)` constructor without keyword still produces an active user — the seeded admin row plus the future register/invite flow constructors all stay backwards-compatible).
  - `last_active_at: datetime.datetime | None = Field(default=None, sa_column=Column(UTCDateTime, nullable=True))` (matches the migration's `nullable=True`; reuses the `UTCDateTime` decorator from `apps/api/app/core/db/models/_helpers.py:19-37` per the `totp_enabled_at` precedent for tz-aware datetimes on SQLite).
- And the field ordering in the class body MUST be: `..., totp_enabled_at, is_active, last_active_at, created_at, last_login_at` (insert the two new fields between the 2FA block and the existing `created_at`/`last_login_at` block, preserving stable serialization order for any caller that snapshots field names via `User.model_fields.keys()`).
- And `apps/api/app/core/db/seed.py:seed_admin()` MUST NOT need modification — the `User(...)` constructor with the existing args already produces `is_active=True, last_active_at=None`; verify by running the existing `test_seed.py::test_seed_admin_creates_admin_row` and asserting it stays green (no test edit needed in this story).

**AC-3 — `LastActiveMiddleware` in NEW `apps/api/app/core/auth/middleware.py` realizes the `SET NX EX 300` throttle per Decision I.**

- Given the architecture decision at `_bmad-output/planning-artifacts/architecture.md:1601-1630` (Decision I) and the existing rate-limit middleware precedent at `apps/api/app/core/auth/ratelimit.py:163-260`,
- When Story 8.1 ships,
- Then `apps/api/app/core/auth/middleware.py` MUST exist as a NEW module with a top-of-file docstring citing Decision I + linking to `architecture.md §1601-1630` (mirroring `ratelimit.py:1-17` precedent shape).
- And the module MUST export a class `LastActiveMiddleware` with the ASGI signature `__init__(self, app: ASGIApp)` (NO scope/key_fn/threshold params — this middleware has zero configurability; the 300s TTL is hardcoded with a module-level constant `_LAST_ACTIVE_THROTTLE_SECONDS = 300` plus an inline comment "matches Decision I + NFR5-PERF-1 verbatim").
- And `__call__(self, scope: Scope, receive: Receive, send: Send)` MUST:
  1. Return immediately if `scope["type"] != "http"` (websocket / lifespan pass-through, matching `ratelimit.py:189-191`).
  2. Decode the `portal_access` cookie via the same path as `apps/api/app/core/auth/dependencies.py:_decode()` — pull the cookie value from `scope["headers"]` (Starlette stores them as a list of `(bytes, bytes)` tuples; use the existing pattern from `ratelimit.py:117-129` `_client_ip` shape for tuple parsing, OR build a `Request(scope, receive)` instance and read `request.cookies[ACCESS_COOKIE]` — implementer's call, prefer whichever produces fewer allocations). If the cookie is absent OR decoding raises `TokenError`, pass the request through with no throttle attempt (`await self.app(scope, receive, send); return`).
  3. Extract `user_id = uuid.UUID(claims["sub"])` from the decoded claims; if the role is not in `{"admin", "member"}` (i.e. the `agent` service account, see below), pass through with no throttle attempt — the agent role's `last_active_at` is structurally unused (no admin panel surfaces it) AND would inflate the audit/throttle Redis namespace with high-frequency machine traffic. **Binding rationale:** the `agent` role posts ingestion every few minutes; if it shared the throttle namespace, its Redis key would always be present, but the DB column would still update once per 5min — that's correct but pollutes the per-user Redis namespace for no operator value. Skipping `agent` is the minimum-surface choice.
  4. Build the Redis key `last_active:{user_id}` (matching Decision I §1612 verbatim — note the `last_active:` prefix, NOT `user:last_active:` as the architecture pseudocode shows; the doc has a 1-character drift that we resolve here in favor of the shorter prefix matching the `ratelimit:` + `invite:reset:` + `totp:partial:` precedent shape from `apps/api/app/modules/auth/router.py:48`).
  5. Call `redis.set(key, now_iso, nx=True, ex=300)` (the `cast=bool` return value indicates acquired-vs-already-present; **must** use `await` since `RedisFactory.get()` returns an async client per `apps/api/app/core/redis.py:1-13`). On Redis exception (`redis.exceptions.ConnectionError`, `redis.exceptions.TimeoutError`, `OSError`), log a single `_LOG.warning("last_active.redis_unavailable", extra={...})` line matching the `ratelimit.py:215-227` fail-soft shape and pass through (DO NOT 5xx, DO NOT block the request — the operator-visible cost of failing a real request because Redis hiccupped is far higher than the cost of one missed `last_active_at` update).
  6. If `acquired is True`, execute a synchronous DB `UPDATE user SET last_active_at = :now WHERE id = :user_id` against the same engine the request handler uses (use `app.state.engine` if it's wired, else fall back to `apps.core.db.session.get_engine()` — verify the engine wiring path by reading `apps/api/app/main.py:lifespan()`). The UPDATE happens AFTER the response is yielded back to the client (per the ASGI middleware idiom of doing work AFTER `await self.app(...)`); if doing pre-handler is simpler, that's acceptable because the DB write is non-blocking from the user's perspective either way — implementer's call. **Critical:** if the UPDATE raises (DB disconnect, FK violation), wrap in a try/except + log a single warning + swallow; never let a `last_active_at` write failure escape and 5xx the request. The throttle column is best-effort signal, not transactional state.
  7. If `acquired is False`, do nothing further (Redis already had the key — another request in this 300s window already wrote — fall through without a DB call).
- And `apps/api/app/main.py:create_app()` MUST register the middleware with `app.add_middleware(LastActiveMiddleware)` placed AFTER the existing `install_csrf_middleware(app)` call AND the four `app.add_middleware(RateLimitMiddleware, ...)` calls; the LIFO wrapping order under Starlette means the install order is the INVERSE of execution order (existing `main.py:84-92` comment block explains this verbatim). So the install sequence becomes: rate-limit trio (added first, innermost) → CSRF (next) → LastActive (LAST, outermost). Concretely the new `add_middleware` line is inserted on the line AFTER `install_csrf_middleware(app)` in `main.py:127`.
- And `LastActiveMiddleware.__call__` MUST NOT raise on the unauthenticated path even when `app.state.redis` is None (defensive against the very early startup window before `lifespan()` populates `app.state.redis = RedisFactory(...)`; if `getattr(request.app.state, "redis", None) is None`, pass through with no log line because this is the legitimate dev / pytest startup window, not a Redis outage).

**AC-4 — Backend tests for the throttle invariant (`test_last_active_middleware.py`, NEW; 6 named tests T1-T6 binding the AC-3 behavior).**

- Given a fakeredis-backed test client + a seeded `member`-role user with a valid `portal_access` cookie,
- When Story 8.1 ships,
- Then `apps/api/tests/test_last_active_middleware.py` MUST exist as a NEW file with six tests:

  | # | Name | Asserts |
  |---|------|--------|
  | T1 | `test_authenticated_request_writes_last_active_on_first_hit` | One GET `/api/auth/me` (or any authenticated endpoint — pick the one most stable across stories) → `user.last_active_at` is non-NULL in DB; Redis key `last_active:{user_id}` exists with TTL ≤ 300. |
  | T2 | `test_throttle_skips_db_write_within_window` | 50 sequential authenticated GETs from the same user within wall-clock <1s → assert SQLAlchemy `before_cursor_execute` event captured EXACTLY 1 `UPDATE user SET last_active_at` statement (use `sqlalchemy.event.listens_for(engine, "before_cursor_execute")` at fixture scope, accumulate matching statements via regex on the SQL text, snapshot count via post-test assertion). |
  | T3 | `test_throttle_allows_second_write_after_ttl_expiry` | First batch of 10 requests → 1 update → advance `time.time` past 300s (use `freezegun.freeze_time` OR `monkeypatch.setattr("time.time", lambda: BASELINE + 301)` — implementer's call; fakeredis honors TTL via its own internal clock so the `await fake.set(...)` TTL countdown is driven by fakeredis-time which is `time.time`-coupled by default) → second batch of 10 requests → 2 total updates. |
  | T4 | `test_anonymous_requests_produce_no_update` | 20 requests with NO `portal_access` cookie set → 0 updates; Redis key namespace is empty. |
  | T5 | `test_agent_role_produces_no_update` | Seeded `agent`-role user, valid cookie, 10 authenticated requests → 0 updates; Redis key for agent user_id absent. Binds the AC-3 step 3 agent-skip rule. |
  | T6 | `test_redis_down_passes_through_with_warning` | Mock the `app.state.redis.get()` to return a client whose `.set(...)` raises `redis.exceptions.ConnectionError` → 1 authenticated GET → handler returns 200 (request succeeded) + `caplog` captures exactly one `WARNING` with `event.action == "last_active.redis_unavailable"` + `user.last_active_at` in DB remains NULL (no DB write attempted on Redis-down path). |

- And the test file MUST use the per-file `client` fixture pattern from `test_2fa_enrollment.py:50-74` for T1-T5 + a fakeredis-with-injected-error fixture variant for T6.
- And T2 + T3 MUST capture SQL statements via SQLAlchemy event listener, NOT via parsing logs or counting audit rows (the `UPDATE user SET last_active_at` doesn't emit an audit row — this is a signal column, not a mutation tracked by `audit.py`). Listener registration pattern: `sqlalchemy.event.listens_for(get_engine(), "before_cursor_execute")(lambda *args, **kwargs: ...)` registered inside the test fixture, cleaned up via `event.remove(...)` in fixture teardown.
- And the test fixture for the seeded user MUST commit the user row to DB BEFORE the request runs (the throttle's UPDATE checks `WHERE id = :user_id`; if the user row isn't there, the UPDATE silently affects zero rows and the test would spuriously pass T2 — guard against this by asserting `session.exec(select(User).where(User.id == user.id)).first()` returns a row pre-request).

**AC-5 — `audit.py` `user` entity_type comment block documents the 6 Epic 8 action names.**

- Given the existing `KNOWN_ENTITY_TYPES` comment block at `apps/api/app/core/audit.py:11-37` (specifically the `user` entry at lines 30-37),
- When Story 8.1 ships,
- Then the comment block for the `user` entity_type MUST be extended to list the 6 future Epic 8 emissions:
  ```python
  #   user                 — auth.login.success/fail; auth.totp.enrolled (Story 7.2);
  #                          auth.totp.verify.success/auth.totp.verify.fail (Story 7.3 +
  #                          7.5 re-auth gates use method=regenerate_reauth/disable_reauth);
  #                          auth.recovery_codes.regenerated (Story 7.5);
  #                          auth.totp.disabled (Story 7.5);
  #                          user.role_changed, user.deactivated, user.reactivated,
  #                          user.force_logout (Story 8.3);
  #                          auth.totp.enrolled (actor!=target, force_enrolled=true),
  #                          auth.totp.disabled (actor!=target, admin_override=true) (Story 8.4);
  #                          auth.password.reset.initiated, auth.password.reset.completed
  #                          (Story 8.5)
  ```
- And the comment MUST cite the planned story per action name so the comment serves as a registry/index across Initiative 5.
- And `KNOWN_ENTITY_TYPES` frozenset MUST remain at 14 entries — NO new entity_type added in this story (the 6 action names all emit against `entity_type="user"` which is already present; the `recovery_code` entity_type added in Story 7.1 covers the `auth.recovery_code.used` action which is unaffected here).
- And the existing test `apps/api/tests/test_audit.py::test_known_entity_types_covers_all_call_site_resources` MUST stay green without modification (the hardcoded expected set in that test contains 14 entries; we add zero, so the assertion holds — no test edit needed).

**AC-6 — `check-all.sh` gains 3 new systemic gates per Epic 7 retro action items §1 + §2.**

- Given the existing `infra/scripts/check-all.sh` 10 stages (verified `ruff format` + `ruff check` for api + workers/render; web `typecheck` + `lint` + `vitest`; pytest for api + workers/render; web `test:visual`),
- When Story 8.1 ships,
- Then `infra/scripts/check-all.sh` MUST gain 3 new stages, inserted in fast-to-slow order (the script's existing convention — stages 1-N are roughly cheapest first, ruff format → ruff check → typecheck → lint → vitest → pytest → visual):
  1. **Stage `settings-env-compose-diff`** (cheap, no external deps, runs in <1s) — a NEW helper invocation (implement as a Python one-liner in the script body OR a small `infra/scripts/check-settings-env-compose.py` helper invoked from the bash; implementer's call) that:
     - Parses `apps/api/app/core/config.py` Settings class to extract every field name (use `apps/api/.venv/bin/python -c "from app.core.config import Settings; print('\n'.join(Settings.model_fields.keys()))"`).
     - Reads `infra/env.example` and extracts every line matching `^([A-Z_]+)=` (uppercase snake var name; ignore comments + blank lines).
     - Reads `infra/docker-compose.yml` and extracts every `services.api.environment` key (use `yq` if available, fallback to `grep -E '^\s+[A-Z_]+:' infra/docker-compose.yml` scoped to the api service block).
     - Computes set difference both ways: every Settings field MUST exist in env.example (uppercase) AND in docker-compose env block; every env.example var MUST map to a Settings field. Stage FAILS with a structured error message listing the missing entries on either side.
     - Known intentional drift exceptions (the script's "allowed-missing" list): `PORTAL_VERSION`, `ENVIRONMENT`, `COOKIE_SECURE`, `CATALOG_HOST_DIR`, `RENDERS_HOST_DIR`, `STATE_HOST_DIR`, `CACHE_HOST_DIR`, `CONTENT_HOST_DIR` — these are infra/compose-only vars NOT in the Pydantic Settings class. Maintain this exception list inline in the helper as a `KNOWN_INFRA_ONLY` constant with a header comment explaining why each entry is exempt.
  2. **Stage `uv-lock-check`** (runs `uv lock --check` against `apps/api/pyproject.toml` then `workers/render/pyproject.toml`; ~1-2s each on a warm machine) — wraps each invocation with the existing `run_stage` helper to keep the per-stage telemetry consistent. FAILS if either `uv lock --check` exits non-zero (indicates `pyproject.toml` changed without `uv lock` regen).
  3. **Stage `local-env-secrets`** (cheap; <1s) — reads `infra/env.example` lines matching `^([A-Z_]+)=$` (empty-on-purpose secret slots: `JWT_SECRET=`, `TOTP_FERNET_KEY=`, etc.). For each one, asserts the same name exists in `infra/.env` with a non-empty value (`grep -E "^${name}=." infra/.env`). FAILS with a list of unset secrets. **Skips gracefully** if `infra/.env` does not exist (fresh checkout, no local dev yet) — emits a `[skip] local-env-secrets (no infra/.env)` line and exits the stage with success. This avoids breaking the script for contributors who haven't yet copied `env.example → .env`.
- And the 3 stages MUST be skippable via the existing `SKIP_<NAME>=1` pattern from `check-all.sh:21-28` — concretely `SKIP_SETTINGS_ENV=1`, `SKIP_UV_LOCK=1`, `SKIP_LOCAL_ENV_SECRETS=1`.
- And running `infra/scripts/check-all.sh` on a clean main branch (post Story 8.1 merge) MUST return all 13 stages green (`10/10 → 13/13`). Verifiable: the dev commit message ends with `13/13 green` per the AGENTS.md `check-all.sh` discipline.

**AC-7 — Conftest `client` fixture promoted; existing per-file fixtures stay in place (no mass refactor in this story).**

- Given the per-file `client` fixture pattern in `test_2fa_enrollment.py:50-74` + `test_2fa_verify.py` + `test_2fa_regenerate.py` + `test_2fa_disable.py` + `test_enforce_2fa_login.py` + `test_invite_admin.py` + `test_invite_register.py` + `test_share_admin.py` + `test_share_service.py` + `test_admin_audit.py` (10 callsites — saturation threshold per Epic 6 retro item §4 + Epic 7 retro item §6),
- When Story 8.1 ships,
- Then `apps/api/tests/conftest.py` MUST gain a NEW `@pytest.fixture` named `client` (preserving the existing `client` fixture if any exists in the file already — verify by reading the file first; if `client` is already defined at conftest scope, this AC is partially satisfied and the implementer may extend the existing one) with the shape:
  - Takes `tmp_path` + `monkeypatch` as args.
  - Sets `DATABASE_URL`, `ADMIN_EMAIL=admin@localhost.localdomain`, `ADMIN_PASSWORD=pw`, `JWT_SECRET="test-secret-not-real"`, `TOTP_FERNET_KEY=ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=` (the deterministic test key from Story 7.1).
  - Clears `get_settings.cache_clear()` + `get_engine.cache_clear()` before AND after the test (frame the body in try/finally per `test_2fa_enrollment.py:73-74`).
  - Constructs `app = create_app()`, attaches a `fakeredis.aioredis.FakeRedis()` instance behind a `MagicMock` factory with `.get()` returning the fake + an awaitable `aclose()`, yields a tuple `(TestClient, FakeRedis)` after wrapping the app in `TestClient(app)` with `c.headers.update({"X-Portal-Client": "web"})`.
- And the fixture MUST be documented with a docstring (3-5 lines) explaining: when to use it (new Epic 8+ test files), why per-file duplicates are NOT being deleted in this story (mass refactor would balloon the diff and risk subtle behavior drift in 10 test files — that refactor lands opportunistically when each file is next touched OR as a separate dedicated `chore(tests)` commit), and what state isolation it provides (fresh DB + fakeredis per test).
- And the existing per-file `client` fixtures MUST NOT be removed in this story (their callers continue to bind to the local-scope definition per pytest's nearest-conftest resolution rule). Verifiable: `git diff` for this story's tests-folder changes shows ONLY the conftest.py insertion + the NEW `test_last_active_middleware.py` + the NEW `test_migration_0014.py`; existing test files are touched ZERO times for fixture migration (touched only if AC-8 below requires it).
- And `apps/api/tests/test_last_active_middleware.py` (AC-4) MUST use the conftest `client` fixture, NOT define its own — this story's NEW test file is the first consumer of the promoted fixture, proving the promotion works.

**AC-8 — Opportunistic ride-along: `auth.login.success` threads X-Request-ID at the single-factor login emission.**

- Given the single-factor login emission site at `apps/api/app/modules/auth/router.py:login()` (the branch that runs when `user.totp_enabled_at IS NULL`, immediately after successful password verify + cookie set),
- When Story 8.1 ships,
- Then the `record_event(action="auth.login.success", ...)` call on that branch MUST thread `request_id=request.headers.get("x-request-id")` as a keyword arg (the existing `record_event` signature at `apps/api/app/core/audit.py:49-58` already accepts this kwarg; the partial-auth + verify-second-factor emission paths already pass it correctly per epic-7-retro-2026-05-20.md:47).
- And a NEW test in `apps/api/tests/test_auth_login_logout.py` (extend the existing file; do NOT create a NEW test file for one assertion) named `test_login_success_threads_x_request_id` MUST assert that when the login request carries `X-Request-ID: test-correlation-uuid-abc`, the resulting `audit_log.request_id` column for the emitted row equals `"test-correlation-uuid-abc"`.
- And the test MUST cover ONLY the single-factor branch (`totp_enabled_at IS NULL`); the partial-auth + verify branches are already covered by Story 7.3 tests and need no new assertion here.
- **Critical scope guard:** this is a ONE-line modification to the existing login handler. Implementer must NOT refactor the surrounding code, MUST NOT add request_id threading to other emission sites in this story (Story 8.3 + 8.4 + 8.5 own their own audit-emission discipline; cleanup-by-stealth across the codebase belongs in a separate `chore(api): audit request_id propagation` commit triaged via `triage-backlog.md` if it accumulates as a pattern).

**AC-9 — Opportunistic ride-along: TOTP_FERNET_KEY rotation triage entry.**

- Given the existing `_bmad-output/triage-backlog.md` file structure (entries are H3-section blocks with metadata fields),
- When Story 8.1 ships,
- Then `_bmad-output/triage-backlog.md` MUST gain ONE new entry block titled `### TOTP_FERNET_KEY rotation runbook` with:
  - **Source:** Epic 7 retrospective action item §10 (carry-over from Epic 6 retro item §8).
  - **Estimated trigger date:** 2027-05-20 (+12 months from Epic 7 close at 2026-05-20).
  - **Owner:** Claude (autonomous, ITCM mode).
  - **Action:** Author a runbook in `docs/operations.md` (or as a standalone `docs/runbooks/totp-fernet-key-rotation.md` — implementer's call at trigger time) covering: (1) generate new key + add as `TOTP_FERNET_KEY_PRIMARY` while keeping old as `TOTP_FERNET_KEY_SECONDARY`; (2) modify `apps/api/app/modules/auth/totp/service.py` to encrypt with primary + try-decrypt with primary-then-secondary; (3) wait for all active `totp_secret` rows to drop through one regen cycle (or hard-cutover by force-re-enrollment via Story 8.4 endpoint); (4) remove secondary; (5) audit-emit `auth.totp.fernet_rotated` (new action name; new audit vocabulary entry needed at that future story).
  - **Status:** triaged (not started; not blocking any open work).
  - **Cross-reference:** epic-7-retro-2026-05-20.md action item §10; epic-6-retro-2026-05-19.md item §8 carry-over.
- And the entry MUST be inserted in the file's existing chronological/priority order (read the file first to see if entries are sorted; preserve whatever discipline exists).

**AC-10 — Pre-flight grep checklist (Story 8.1 close-out invariants, per Story 7.1 AC-10 precedent).**

Before the dev commit lands, the developer agent MUST run the following greps and confirm each returns silent success (matching the Story 7.1 close-out discipline at `apps/api/tests/test_2fa_schema.py:1-* T14 verification block`):

1. `grep -rn "agent" apps/api/app/core/auth/middleware.py` returns ≥1 line matching the role-skip branch (AC-3 step 3 enforcement — confirms the `agent` role is explicitly handled).
2. `grep -rn "last_active:" apps/api/app/core/auth/middleware.py` returns ≥1 line matching the Redis key prefix (AC-3 step 4 enforcement).
3. `grep -rn "300" apps/api/app/core/auth/middleware.py` returns ≥1 line (the throttle TTL constant — confirms it's not been silently softened to 60 or 600 during implementation).
4. `grep -rn "is_active\|last_active_at" apps/api/migrations/versions/0014_users_is_active_last_active.py` returns ≥2 lines per column (one in `upgrade`, one in `downgrade`).
5. `grep -rn "TOTP_FERNET_KEY" _bmad-output/triage-backlog.md` returns the new triage entry (AC-9).
6. `grep -rn "settings-env-compose-diff\|uv-lock-check\|local-env-secrets" infra/scripts/check-all.sh` returns 3+ matching lines (AC-6 enforcement — confirms the 3 stages were added).
7. `grep -rn "user.deactivated\|user.reactivated\|user.role_changed\|user.force_logout" apps/api/app/core/audit.py` returns 4+ matching lines in the comment block (AC-5 enforcement — confirms the docstring update landed; this is a comment-only grep, NOT an emission check — Story 8.3 owns the emissions).
8. `infra/scripts/check-all.sh` returns `13/13 green` end-to-end against the dev commit (the new 3 stages all pass on the dev branch).
9. `apps/api/tests/test_audit.py::test_known_entity_types_covers_all_call_site_resources` stays green (no entity_type added in this story).
10. `git log --oneline --decorate -5` does NOT show a partial-implementation commit (the dev commit is a single squashed atomic commit landing all 5 NEW files + ~10 modified files + the chore bundle).

All 10 greps + the green check-all.sh exit are AC-10 binding; a failure on any of them is a pre-merge blocker.

## Tasks / Subtasks

- [ ] **T1 — Author Alembic migration `0014_users_is_active_last_active.py`** (AC-1)
  - [ ] T1.1 Read `apps/api/migrations/versions/0013_users_2fa_columns.py` end-to-end to match docstring + structural conventions verbatim.
  - [ ] T1.2 Author the migration file with `revision`/`down_revision` chain + docstring + `upgrade()` adding both columns + `downgrade()` strict-LIFO drop.
  - [ ] T1.3 Verify locally: `cd apps/api && .venv/bin/alembic upgrade head` against a tmpdir SQLite DB succeeds; `PRAGMA table_info(user)` shows both new columns; `.venv/bin/alembic downgrade -1 && .venv/bin/alembic upgrade head` is clean.

- [ ] **T2 — Extend `User` SQLModel with the 2 new fields** (AC-2)
  - [ ] T2.1 Read `apps/api/app/core/db/models/_user.py` end-to-end; pick the insertion point (between `totp_enabled_at` and `created_at`).
  - [ ] T2.2 Add `is_active: bool = Field(default=True)` + `last_active_at: datetime.datetime | None = Field(default=None, sa_column=Column(UTCDateTime, nullable=True))`.
  - [ ] T2.3 Verify `apps/api/.venv/bin/python -c "from app.core.db.models import User; u = User(email='x', display_name='y', role='member', password_hash='z'); print(u.is_active, u.last_active_at)"` prints `True None`.
  - [ ] T2.4 Run existing `apps/api/tests/test_seed.py::test_seed_admin_creates_admin_row` and assert it stays green (constructor backwards-compat).

- [ ] **T3 — Author `LastActiveMiddleware` in NEW `apps/api/app/core/auth/middleware.py`** (AC-3)
  - [ ] T3.1 Read `apps/api/app/core/auth/ratelimit.py:1-260` end-to-end for the middleware shape, fail-soft pattern, and ASGI scope handling.
  - [ ] T3.2 Read `apps/api/app/core/auth/dependencies.py:_decode()` for the JWT cookie decode path; reuse `decode_token` + `ACCESS_COOKIE` imports.
  - [ ] T3.3 Read `apps/api/app/core/redis.py` to confirm `RedisFactory.get() -> Redis (async client)`; the middleware calls `await client.set(...)`.
  - [ ] T3.4 Author `middleware.py` per AC-3 steps 1-7 with module-level docstring citing Decision I.
  - [ ] T3.5 Wire into `apps/api/app/main.py:create_app()` per AC-3 LIFO ordering rule (one new line right after `install_csrf_middleware(app)` and before the `@app.get("/api/health")` block).

- [ ] **T4 — Write `apps/api/tests/test_migration_0014.py` round-trip test** (AC-1)
  - [ ] T4.1 Copy `test_migration_0012.py:38-99` round-trip + fixture pattern verbatim.
  - [ ] T4.2 Adapt assertions to 0014's columns + drop sequence.
  - [ ] T4.3 Verify locally: `cd apps/api && .venv/bin/pytest tests/test_migration_0014.py -v` is green.

- [ ] **T5 — Promote `client` fixture to `conftest.py`** (AC-7)
  - [ ] T5.1 Read `apps/api/tests/conftest.py` end-to-end to identify the insertion point and confirm no existing `client` fixture name collision.
  - [ ] T5.2 Add the new fixture per AC-7 shape with docstring.
  - [ ] T5.3 Verify by running ALL of `apps/api/tests/test_2fa_*.py` + `test_invite_*.py` + `test_share_*.py` + `test_admin_audit.py` → all stay green (the per-file fixtures still win via pytest's nearest-resolution rule; the conftest fixture is dormant until a NEW test file consumes it).

- [ ] **T6 — Write `apps/api/tests/test_last_active_middleware.py` with the 6 named tests** (AC-4)
  - [ ] T6.1 Author the fixture using the new conftest `client` fixture (AC-4 verbatim binding).
  - [ ] T6.2 Implement the SQLAlchemy `before_cursor_execute` event-listener helper for SQL statement capture; register in fixture, remove in teardown.
  - [ ] T6.3 Implement T1-T6 per the AC-4 table; verify each in isolation then together.
  - [ ] T6.4 Verify `cd apps/api && .venv/bin/pytest tests/test_last_active_middleware.py -v` is green for all 6.

- [ ] **T7 — Extend `audit.py` `user` entity_type comment block with 6 E8 action names** (AC-5)
  - [ ] T7.1 Read `apps/api/app/core/audit.py:1-50` end-to-end.
  - [ ] T7.2 Extend the `user` block per AC-5 shape (cite stories 8.3, 8.4, 8.5 for each action name group).
  - [ ] T7.3 Verify `apps/api/tests/test_audit.py::test_known_entity_types_covers_all_call_site_resources` stays green (no entity_type added — pure comment update).

- [ ] **T8 — Patch single-factor `auth.login.success` to thread X-Request-ID** (AC-8)
  - [ ] T8.1 Read `apps/api/app/modules/auth/router.py:login()` to locate the single-factor emission branch.
  - [ ] T8.2 Add `request_id=request.headers.get("x-request-id")` to the `record_event(...)` call on the single-factor branch.
  - [ ] T8.3 Extend `apps/api/tests/test_auth_login_logout.py` with `test_login_success_threads_x_request_id` per AC-8 shape.
  - [ ] T8.4 Verify the test is green AND every existing test in `test_auth_login_logout.py` stays green.

- [ ] **T9 — `check-all.sh` 3 new stages** (AC-6)
  - [ ] T9.1 Read `infra/scripts/check-all.sh:1-N` end-to-end to understand the `run_stage` helper + `SKIP_*` pattern.
  - [ ] T9.2 Add stage `settings-env-compose-diff` per AC-6 step 1 (Python one-liner OR small helper script — implementer's call).
  - [ ] T9.3 Add stage `uv-lock-check` per AC-6 step 2 (calls `uv lock --check` in both `apps/api/` and `workers/render/`).
  - [ ] T9.4 Add stage `local-env-secrets` per AC-6 step 3 (graceful skip if `infra/.env` is absent).
  - [ ] T9.5 Run `infra/scripts/check-all.sh` from repo root; verify all 13 stages return green (use `SKIP_VISUAL=1` if needed for fast iteration during dev, but the final pre-commit run MUST be unrestricted with all 13/13 green).

- [ ] **T10 — TOTP_FERNET_KEY rotation triage entry** (AC-9)
  - [ ] T10.1 Read `_bmad-output/triage-backlog.md` end-to-end to understand entry format + chronological order.
  - [ ] T10.2 Add the new entry per AC-9 shape at the appropriate insertion point.

- [ ] **T11 — Run AC-10 pre-flight grep checklist** (AC-10)
  - [ ] T11.1 Execute each of the 10 greps + `check-all.sh` + targeted pytest commands.
  - [ ] T11.2 If any grep returns unexpected output, fix the underlying gap before committing.

- [ ] **T12 — Dev commit + sprint-status flip** (close-out)
  - [ ] T12.1 Single squashed `feat(api,infra,tests): ...` commit covering all 5 NEW files + ~10 modified files.
  - [ ] T12.2 Commit message follows the AGENTS.md convention (subject ≤72 chars; body cites Decision I + epics §1749 + Epic 7 retro action items §1+§2+§6+§8+§10; trailer `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`).
  - [ ] T12.3 Update sprint-status: flip `8-1-alembic-0014-is-active-last-active-middleware` from `ready-for-dev` → `review` (NOT `done` — Codex review comes next per Epic 7 retro action item §3 fixed-point loop discipline).
  - [ ] T12.4 If this is the first Epic 8 story (it is — Epic 8 starts here), confirm `epic-8` status flips from `backlog` → `in-progress` per the bmad-create-story workflow's step 1 enforcement.

## Dev Notes

### Architectural anchors

- **Decision I** (`_bmad-output/planning-artifacts/architecture.md:1601-1630`) — the binding spec for `is_active` + `last_active_at` columns + `LastActiveMiddleware` + `SET NX EX 300` throttle primitive. Read in full before T3.
- **Epics anchor** (`_bmad-output/planning-artifacts/epics.md:1749-1761`) — the Story 8.1 acceptance check shape. Read in full to confirm scope.
- **Epic 7 retrospective action items** (`_bmad-output/implementation-artifacts/epic-7-retro-2026-05-20.md:197-272`) — actions §1, §2, §6, §8, §10 are bundled into this story per the retro's explicit recommendation that Story 8.1 carry the tooling-debt close-out.
- **Story 7.1 precedent** (`_bmad-output/implementation-artifacts/7-1-alembic-0013-2fa-columns-recovery-codes.md:784-854`) — the Alembic + Settings + tests pattern Story 8.1 mirrors. Read the Dev Agent Record section to understand the in-session friction Story 7.1 encountered (FK ordering on single-flush, UoW topological sort drift; `inspect(engine).get_indexes` returning `unique=0` not `False` on SQLite); these are NOT expected to repeat in Story 8.1 because we're not adding a FK or an index, but the conftest discipline learned there applies.

### Critical files to read before touching

- `apps/api/app/core/auth/ratelimit.py` (the middleware structural precedent — fail-soft, ASGI scope handling, Redis pipeline + try/except).
- `apps/api/app/core/auth/dependencies.py` (JWT decode helpers — `_decode`, `ACCESS_COOKIE`).
- `apps/api/app/main.py:lifespan() + create_app()` (the middleware install LIFO ordering; `app.state.redis` wiring; `app.state.engine` if present).
- `apps/api/migrations/versions/0013_users_2fa_columns.py` (Alembic file shape + docstring conventions).
- `apps/api/app/core/db/models/_user.py` (the field insertion point + `UTCDateTime` decorator usage).
- `apps/api/app/core/db/models/_helpers.py:UTCDateTime` (the timezone-aware DateTime type decorator).
- `apps/api/tests/test_migration_0012.py` (the round-trip fixture pattern verbatim).
- `apps/api/tests/test_2fa_enrollment.py:1-90` (the per-file `client` fixture pattern; the conftest promotion in T5 mirrors this shape).
- `infra/scripts/check-all.sh` (the `run_stage` helper + `SKIP_*` pattern + stage ordering).
- `infra/env.example` (the env-var name list — needs to be diff-able by the new `settings-env-compose-diff` stage).
- `infra/docker-compose.yml` (the `services.api.environment` block — same).
- `apps/api/app/core/config.py:Settings` (the field list — same).

### Library/framework versions to respect

- **Alembic ≥1.14** — `op.add_column`, `op.drop_column`, `sa.Column(..., server_default=sa.text("1"))` are the canonical idioms. Do NOT use `op.execute("ALTER TABLE ...")` for column additions — alembic's ORM-aware path generates the same SQL but with the round-trip discipline (the `op.batch_alter_table` context is required ONLY for SQLite multi-column constraint changes; single-column add does NOT need it per the `0013_users_2fa_columns.py:46-66` precedent which uses bare `op.add_column`).
- **SQLModel 0.0.22** — `Field(default=...)` for plain Python-typed columns; `Field(default=..., sa_column=Column(...))` ONLY when overriding the DB-side type (e.g. UTCDateTime decorator). For the `is_active: bool` field, bare `Field(default=True)` is correct — SQLModel auto-infers `Column(Boolean, nullable=False)` and the `default=True` propagates to the SQL DEFAULT.
- **Pydantic 2.9** — `Settings.model_fields.keys()` is the v2 API for field introspection (NOT v1's `__fields__`). The `settings-env-compose-diff` stage uses this.
- **Redis client 5.2** — `Redis.set(key, value, nx=True, ex=300)` returns `bool` (True if set, False if already exists). The async client mirror at `redis.asyncio.Redis` has the same signature; `await redis.set(...)` returns the same bool.
- **uv ≥0.5** (workspace-managed) — `uv lock --check` returns exit 0 if lockfile is up-to-date, non-zero otherwise. The `--check` flag is the canonical CI gate per uv docs.
- **fakeredis ≥2.x** — `fakeredis.aioredis.FakeRedis()` is the async-API mirror; honors TTL via `time.time` coupling, which is monkeypatchable per T3 in AC-4.
- **pytest 8.x + sqlalchemy 2.x** — `sqlalchemy.event.listens_for(engine, "before_cursor_execute")` is the canonical SQL statement capture hook; the decorator returns a function reference suitable for `event.remove(engine, "before_cursor_execute", func)` in teardown.

### File structure requirements

- **NEW middleware file MUST live at `apps/api/app/core/auth/middleware.py`** per Decision I §1610 verbatim. Do NOT create `apps/api/app/core/middleware.py` or `apps/api/app/modules/auth/middleware.py` or any other path; the architecture binds the exact path.
- **NEW migration MUST be named `0014_users_is_active_last_active.py`** per epics §1757 verbatim. Do NOT abbreviate to `0014_is_active.py` or expand to `0014_users_soft_delete_and_throttle.py`.
- **NEW tests MUST be named `test_migration_0014.py` + `test_last_active_middleware.py`** matching the Story 7.1 + Story 7.2 file-naming precedent (`test_2fa_schema.py`, `test_2fa_enrollment.py`).
- **Triage entry insertion point** — read `_bmad-output/triage-backlog.md` to determine chronological vs priority order; preserve whatever discipline the file already has.

### Testing requirements

- **AC-4 tests (6 named) MUST pass in isolation AND together.** Run `pytest tests/test_last_active_middleware.py -v` (isolation) and `pytest tests/ -v -k "last_active"` (together-with-related) to catch ordering / fixture-bleed issues.
- **AC-1 round-trip MUST be exercised on SQLite** (the project's only target dialect today). PostgreSQL forward-compat is tested implicitly by SQLModel's dialect-agnostic typing; no separate test needed.
- **Pre-merge full suite green** — `cd apps/api && .venv/bin/pytest -v` returns ALL tests green (current Epic 7 close-out baseline: 690 backend tests passing per epic-7-retro line 307; Story 8.1 adds ~10 new tests landing at ~700). Verifiable via `pytest --co | wc -l` before/after.
- **`infra/scripts/check-all.sh` 13/13 green** — the canonical pre-commit gate.
- **NO Codex P2 fix-ups expected on the middleware itself** — the middleware is a simple ASGI passthrough with one Redis call + one DB call; the Story 7.3 + 7.5 concurrency-race classes (atomic GETDEL, restore-on-fail, commit-guard) do NOT apply here because `SET NX EX` is a single atomic Redis call AND the DB write is fire-and-forget. **HOWEVER:** Codex may surface fix-ups on (a) the `settings-env-compose-diff` helper if it has shell-injection or path-traversal gaps; (b) the X-Request-ID patch if the request_id is None-passable in a way that downstream consumers don't tolerate; (c) the fixture promotion if a subtle behavior drift surfaces between per-file and conftest scope. Expect 0-2 fix-ups per Epic 7's 100% intercept rate baseline.

### Previous story intelligence (Story 7.1 + 7.5 + 7.6 carryover)

- **Story 7.1 production incident class**: forgot to provision `TOTP_FERNET_KEY` in `.190` `infra/.env` before container restart → app fail-fast loop. Story 8.1's `local-env-secrets` stage catches the LOCAL-dev variant of this; the matching `.190` pre-deploy check is deferred to Story 9.x or 10.x. **Operator action required** between Story 8.1 merge and Story 8.3 start: confirm `.190` `infra/.env` has no empty `^[A-Z_]+=$` lines that should be populated; the `check-all.sh` `local-env-secrets` stage gives this confidence on the dev box but not against prod.
- **Story 7.3 partial-auth → verify-second-factor audit-emission split**: the `auth.login.success` emission split between login (single-factor) + verify-second-factor (TOTP / recovery-code paths) was a Story 7.3 architectural decision. AC-8's X-Request-ID patch ONLY touches the single-factor login emission; the partial+verify path is already correct per epic-7-retro line 47.
- **Story 7.5 concurrent-regenerate + cancel + offload pattern**: NOT applicable to Story 8.1's middleware (single Redis call, single DB write, no compound state mutation). The drill-verified pattern catalog (epic-7-retro line 113) is reference material for Story 8.3 + 8.4, not 8.1.
- **Story 7.6 drill-artifact filename convention**: NOT relevant to Story 8.1 (no drill artifact produced here). The convention re-applies in Story 10.x (cutover-smoke).
- **Conftest fixture promotion timing**: Epic 6 retro recommended this at 4-file saturation; Epic 7 escalated to high priority at ~10 files. Story 8.1 is the agreed carrier per epic-7-retro action item §6 (Trigger: bundle into Story 8.1 chore commit).

### Git intelligence (recent commits)

```
9dedc81 fix(infra): Story 7.6 codex fix-up — drill script hardening
1fbba7b chore(infra): add 2fa-recovery-drill.sh — Epic 7 acceptance-gate drill script (Story 7.6)
f325efa fix(api): Story 7.5 codex P2 follow-up — preserve active-only predicate on UPDATE
91d91b6 fix(api,web): Story 7.5 codex P2 follow-up — concurrent regenerate + cancel + offload
477fc7b feat(api,web): regenerate recovery codes + disable TOTP (Story 7.5)
```

Pattern: each story lands as `feat(api[,web,infra,tests]): ...` initial commit, then 1-2 `fix(...)` Codex P2 follow-up commits on the same story-scoped commit-message subject. Story 8.1 should follow the same shape — single `feat(api,infra,tests): ...` initial commit, then Codex review + 0-2 fix-up commits before sprint-status flips `review` → `done`.

### Project Structure Notes

- **Alignment with unified project structure:** all new files land in their natural locations (migrations under `apps/api/migrations/versions/`, middleware under `apps/api/app/core/auth/`, tests under `apps/api/tests/`, infra script changes under `infra/scripts/`, triage entry under `_bmad-output/`). No new top-level directory.
- **Detected conflicts or variances:** none. Decision I's pseudocode at architecture.md §1611-1619 uses Redis key prefix `user:last_active:` whereas this story specifies `last_active:` (shorter, matches the `ratelimit:` + `invite:reset:` + `totp:partial:` precedent). This is a deliberate ~1-char drift resolved in this story; bmad-correct-course can patch architecture.md text at the Epic 8 retro if the operator wants verbatim alignment after the fact.
- **Naming conventions:** `is_active` (snake) is the standard "soft-delete + reactivation" column name across SQL ORM conventions; `last_active_at` (snake + `_at` suffix) is the project's tz-aware-timestamp convention (`created_at`, `last_login_at`, `totp_enabled_at`, `generated_at` precedent).

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-I-Soft-delete-+-last_active_at-throttling`] (lines 1601-1630)
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-8.1`] (lines 1749-1761)
- [Source: `_bmad-output/implementation-artifacts/epic-7-retro-2026-05-20.md#Action-items`] (lines 197-272)
- [Source: `_bmad-output/implementation-artifacts/7-1-alembic-0013-2fa-columns-recovery-codes.md#Dev-Agent-Record`] (lines 784-854) — Story 7.1 precedent
- [Source: `apps/api/app/core/auth/ratelimit.py:163-260`] — middleware structural precedent
- [Source: `apps/api/migrations/versions/0013_users_2fa_columns.py`] — Alembic file shape precedent
- [Source: `apps/api/tests/test_migration_0012.py:38-99`] — round-trip fixture pattern
- [Source: `apps/api/tests/test_2fa_enrollment.py:50-74`] — `client` fixture shape
- [Source: `_bmad-output/project-context.md`] — FastAPI / SQLModel / auth conventions
- [Source: `AGENTS.md`] — repo layout + commit conventions
- [Source: `_bmad-output/triage-backlog.md`] — entry format for AC-9
- [Source: `infra/scripts/check-all.sh`] — `run_stage` helper + SKIP_* pattern

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m]

### Debug Log References

### Completion Notes List

### File List
