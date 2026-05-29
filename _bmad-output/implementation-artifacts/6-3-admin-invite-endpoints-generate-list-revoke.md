# Story 6.3: Admin endpoints — invite generate / list / revoke

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want a new `apps/api/app/modules/invite/admin_router.py` exposing three admin-only HTTP endpoints (`POST /api/admin/invites` to generate, `GET /api/admin/invites` to list with status filter + pagination, `POST /api/admin/invites/{id}/revoke` to revoke) that wrap the Story 6.2 `InviteService` and emit the matching `auth.invite.generated` / `auth.invite.revoked` audit rows via the existing `record_event()` helper,
so that Story 6.4 (public `/register?token=` flow), Story 8.6 (admin-panel Invites tab UI), and the E9 audit can rely on a single tested HTTP surface that mirrors the Init 0 `share/admin_router.py` conventions (filename layout + `_service()` factory + cookie-cleaning audit emission + 401/403/404/409/422 error envelope), one-time cleartext token surfacing in the generate response and **never** in any list response, immediate revoke semantics observable through the public route (`POST /api/auth/register?token=<revoked-token>` returns HTTP 410 Gone in Story 6.4), and the global `X-Portal-Client: web` CSRF guard already enforced by `app/core/auth/csrf.py` middleware.

## Acceptance Criteria

**AC-1 — `POST /api/admin/invites` generate endpoint surfaces cleartext token exactly once + audit row written.**

- Given an admin-authenticated `TestClient` request (cookie `portal_access` with role=admin JWT, `X-Portal-Client: web` header from the conftest fixture default) and the `invite_tokens` table empty,
- When the client posts `{"role": "member", "ttl_preset": "SEVEN_DAYS"}` (or equivalently `{"role": "member", "ttl_seconds": 604800}` — both forms accepted),
- Then the response is HTTP 201 with body shape `{"invite_id": "<uuid>", "token": "<43-char-urlsafe>", "registration_url": "/register?token=<that-token>", "role": "member", "ttl_seconds": 604800, "expires_at": "<ISO-8601 UTC>"}` — the cleartext `token` field appears in this response and **nowhere else** in the API surface (verified by AC-2 list endpoint omission + audit-row omission),
- And `expires_at = generated_at + ttl_seconds` to within ±1 second tolerance, serialized as a tz-aware ISO 8601 UTC string,
- And exactly one row exists in `invite_tokens` with the just-issued `invite_id`, with `generated_by_user_id` equal to the authenticated admin's UUID (decoded from the cookie JWT `sub` claim — same path as `share/admin_router.py` uses `user_id: uuid.UUID = current_admin`), `role == "member"`, `ttl_seconds == 604800`, and `token_hash == hash_token(<cleartext-token-from-response>)` (verified by a fresh `Session(get_engine()).exec(select(InviteToken).where(InviteToken.id == invite_id)).first()`),
- And exactly one Redis key exists at `invite:token:<that-token>` with TTL `604800` (the existing `InviteService.generate_invite()` behaviour from Story 6.2 — this AC verifies the route wires the service correctly, not that it re-implements the dual-write contract),
- And exactly one new `audit_log` row exists with `action="auth.invite.generated"`, `entity_type="invite_token"`, `entity_id=<invite_id>`, `actor_user_id=<admin_uuid>`, `request_id=<value-from-x-request-id-header-or-None>`, and an `after` JSON payload containing AT LEAST `{"role": "member", "ttl_seconds": 604800}` (the cleartext token MUST NOT appear in the audit row's `after` payload — token-at-rest hygiene per Decision B "cleartext token never returned in any list-invites response"; the audit row exists for "who generated what when", not for token recovery),
- And `POST /api/admin/invites` with `{"role": "agent", "ttl_seconds": 86400}` returns HTTP 422 with body `{"detail": "<error message naming role>"}` and NO `invite_tokens` row + NO Redis key + NO audit row (`InviteService.generate_invite()` raises `ValueError("role must be member or admin")` from Story 6.2 — the router catches `ValueError` and translates to 422). Same 422 path covers `ttl_seconds=59` and `ttl_seconds=7776001` (out-of-range bounds from Decision B).
- And the four `InviteTTLPreset` enum members (`ONE_DAY` / `THREE_DAYS` / `SEVEN_DAYS` / `THIRTY_DAYS`) map to the documented `ttl_seconds` values (86400 / 259200 / 604800 / 2592000); a request with `{"ttl_preset": "ONE_DAY"}` produces a row with `ttl_seconds=86400`. The request schema accepts `ttl_preset` (string-name from the enum) OR `ttl_seconds` (raw int), with mutual exclusivity validated at the schema layer (both supplied → 422 with `"detail": "specify exactly one of ttl_preset, ttl_seconds"`; neither supplied → 422 with the same message).

**AC-2 — `GET /api/admin/invites` lists DB rows with status filter + pagination, never surfaces cleartext token.**

- Given the `invite_tokens` table seeded with 4 rows representing each status — one active (`used_at IS NULL`, `revoked_at IS NULL`, `generated_at` within TTL), one used (`used_at IS NOT NULL`), one expired (`used_at IS NULL`, `revoked_at IS NULL`, `generated_at + ttl_seconds < now`), one revoked (`revoked_at IS NOT NULL`),
- When the client (admin cookie) GETs `/api/admin/invites?status=active`,
- Then the response is HTTP 200 with body shape `{"total": 1, "items": [{"invite_id": "<uuid>", "role": "member", "ttl_seconds": <int>, "generated_by_user_id": "<uuid|null>", "generated_at": "<ISO>", "expires_at": "<ISO>", "used_by_user_id": null, "used_at": null, "used_from_ip": null, "revoked_at": null, "status": "active"}], "page": 1, "page_size": 50}` — `status` is a derived field computed by the router from `(used_at, revoked_at, generated_at + ttl_seconds, now)` (verified by per-row matching against the per-status seed; the column itself is NOT stored),
- And the response NEVER includes a `token` or `token_hash` field (verified by `assert "token" not in items[0]` and `assert "token_hash" not in items[0]`) — per Decision B "cleartext token never returned in any list-invites response" + token-at-rest hashing principle (no clear way to recover cleartext from `token_hash` SHA-256),
- And `GET /api/admin/invites?status=used` returns exactly the used row, `?status=expired` exactly the expired row, `?status=revoked` exactly the revoked row,
- And `GET /api/admin/invites` (no `status` query) returns all 4 rows sorted by `generated_at DESC` (matches the `ix_invite_tokens_generated_at` index from Story 6.1 — DESC is the natural admin-panel "newest first" ordering),
- And `GET /api/admin/invites?page=1&page_size=2` returns 2 items + `total=4` + `page=1` + `page_size=2`; `page=2&page_size=2` returns the next 2; `page=3&page_size=2` returns 0 items + `total=4` (deterministic pagination; rows beyond the last page produce an empty `items` array, NOT 404),
- And `page` validation: `page < 1` → HTTP 422; `page_size < 1` or `page_size > 200` → HTTP 422 (the upper bound `200` is the binding choice; rationale: admin-panel default 50, occasional bulk export at 200 — same shape as `/api/admin/audit?limit=…&offset=…` validation in `admin/router.py` lines 56-57),
- And `status` validation: invalid values (`active|used|expired|revoked|<other>` — `<other>` triggers 422) — only the 4 enum values are accepted. The 4 status names exactly match Decision A + Decision B vocabulary (no `consumed`, `pending`, `inactive` synonyms).
- And the endpoint requires `current_admin`: a member-authenticated cookie returns 403; an anonymous request returns 401 (verified against both `current_user`-resolvable cookies and missing-cookie cases).

**AC-3 — `POST /api/admin/invites/{id}/revoke` revokes + Redis key DEL + audit row written + downstream `/register?token=...` would return 410.**

- Given the `invite_tokens` table has one active row + one Redis key `invite:token:<token>` matching it,
- When admin POSTs `/api/admin/invites/<invite_id>/revoke` with empty body,
- Then the response is HTTP 204 (no body) — same shape as `DELETE /api/admin/share/{token}` in `share/admin_router.py:65-80`,
- And the DB row has `revoked_at` set to a tz-aware UTC datetime within ±5 seconds of `datetime.now(UTC)` (verified via `session.get(InviteToken, invite_id)`),
- And the Redis key `invite:token:<token>` is GONE (verified via `await fake_redis.get(f"invite:token:{<token>}")` is `None` — the SCAN-based key resolution from Story 6.2 `revoke()` already handles this; this AC verifies the wiring, not the SCAN logic),
- And exactly one new `audit_log` row has `action="auth.invite.revoked"`, `entity_type="invite_token"`, `entity_id=<invite_id>`, `actor_user_id=<admin_uuid>`, `request_id=<header-or-None>`, and an `after` payload containing AT LEAST `{"invite_id": "<uuid>"}` — the cleartext token MUST NOT appear in the audit `after` payload (per AC-1 hygiene rule),
- And a subsequent `await InviteService(redis=..., engine=...).validate_active(<cleartext-token>)` returns `None` (Redis key gone → AC verifies the FR5-INVITE-3 contract "a revoked-but-still-shown-in-the-list token MUST NOT be consumable" at the service-layer boundary; Story 6.4 will make the equivalent assertion at the HTTP `/register?token=` level once it ships),
- And `POST /api/admin/invites/<nonexistent-uuid>/revoke` returns HTTP 404 (the router catches `InviteNotFound` from `InviteService.revoke()` and translates to 404; the response body is `{"detail": "invite not found"}` or equivalent — the exact phrasing is open but the status code is binding),
- And `POST /api/admin/invites/<already-used-or-already-revoked-id>/revoke` returns HTTP 409 (the router catches `InviteAlreadyResolved` from `InviteService.revoke()` and translates to 409 — distinct from 404 so the admin UI in Story 8.6 can surface "already consumed/revoked" differently from "row deleted"; the response body is `{"detail": "invite already used or revoked"}` or equivalent),
- And the endpoint requires `current_admin`: member cookie → 403; anonymous → 401; CSRF header missing → 403 with `{"detail": "csrf_required"}` (the global `X-Portal-Client: web` CSRF middleware enforces this; the conftest `client` fixture already sets the header, so this AC's CSRF case is exercised via a dedicated test that strips the header).

**AC-4 — All three endpoints require `current_admin` dependency; member-authenticated requests return 403.**

- Given a `member`-role cookie issued via `encode_token(subject=<member_uuid>, role="member", secret="test", ttl_minutes=30)` (mirroring `test_share_admin.py:64` admin-token construction shape but with `role="member"`),
- When the member cookie is set on the test client and the client hits each of `POST /api/admin/invites`, `GET /api/admin/invites`, `POST /api/admin/invites/<any-uuid>/revoke`,
- Then EACH endpoint returns HTTP 403 with body `{"detail": "admin_required"}` (matches the existing `_resolve_admin()` error envelope in `app/core/auth/dependencies.py:30` — `current_admin` raises 403 with `"admin_required"`),
- And NO `invite_tokens` row is created or modified,
- And NO `audit_log` row is created (the 403 fires INSIDE the dependency resolution, BEFORE the route function body executes, so no service call + no audit emission happens),
- And an anonymous request (no cookie at all) returns HTTP 401 with body `{"detail": "missing_access"}` on each of the three endpoints (matches `_decode()` in `app/core/auth/dependencies.py:18` — token-missing case),
- And an invalid/expired-JWT cookie returns HTTP 401 with body `{"detail": "invalid_access"}` or `{"detail": "access_expired"}` respectively (matches `_decode()` lines 21-24; existing behaviour, no new logic in this story).

**AC-5 — Endpoints follow Init 0 admin-router conventions: filename layout, `_service()` factory, error envelope, CSRF middleware integration.**

- Given the existing Init 0 / Init 5 admin-router patterns established by `apps/api/app/modules/share/admin_router.py` (Init 0 share endpoints, 80 LOC) and `apps/api/app/modules/sot/admin_router.py` (Init 2 SoT endpoints, 1076 LOC),
- When the new `apps/api/app/modules/invite/admin_router.py` is authored,
- Then the file layout follows the share-module convention:
  - File path: `apps/api/app/modules/invite/admin_router.py` (sibling to `service.py` / `models.py` / `__init__.py` — NOT a separate `app/admin/` directory; matches `share/admin_router.py` location),
  - Imports: `APIRouter`, `Depends`, `HTTPException`, `Request`, `Response`, `status` from FastAPI; `Session`, `select` from sqlmodel; `record_event` from `app.core.audit`; `current_admin` from `app.core.auth.dependencies`; `get_engine`, `get_session` from `app.core.db.session`; `InviteService` + the four custom exceptions + `InviteToken` + `InviteTTLPreset` from `app.modules.invite` (the `__init__.py` re-export from Story 6.2 — DO NOT reach into `service.py` / `models.py` directly),
  - Router declaration: `router = APIRouter(prefix="/api/admin/invites", tags=["admin", "invite"])` (matches share-router's tag pattern `tags=["admin", "share"]`),
  - Service factory: `def _service(request: Request) -> InviteService: return InviteService(redis=request.app.state.redis.get(), engine=get_engine())` (mirrors `share/admin_router.py:21-22`, with the dual-backed constructor signature from Story 6.2),
- And the router is registered in `apps/api/app/router.py` between the existing `share_admin_router` and `share_router` `include_router()` calls (alphabetical-by-module order would place it before `share` modules; the binding choice is between-share-and-share to keep all admin routers contiguous — see Dev Notes § "Router registration ordering" for the rationale + line-level placement),
- And NO new top-level main.py edits are needed — `app.state.redis` is already set up by the existing lifespan + `get_engine()` is already cached + CSRF middleware already mounted at `app/main.py:68`,
- And the error envelope matches the FastAPI default `{"detail": "<reason>"}` shape used by every other admin router in the repo — NO custom JSON envelope, NO `{"error": {"code": ..., "message": ...}}` patterns,
- And the route function signatures use the `user_id: uuid.UUID = current_admin` parameter form (default-value style, NOT `Depends(current_admin)` in the function body — matches every existing admin endpoint in `share/admin_router.py:30 / 59 / 69`),
- And the new file passes `ruff format` + `ruff check` cleanly with no `# noqa` exceptions (the repo's strict-clean policy from `pyproject.toml`).

**AC-6 — Request/response schemas live in a new `apps/api/app/modules/invite/admin_schemas.py` file + `__init__.py` re-exports updated + tests green.**

- Given the precedent of `apps/api/app/modules/sot/admin_schemas.py` (request-schemas-only module for the SoT admin router) and `apps/api/app/modules/share/models.py` (mixed SQLModel + Pydantic — Init 0 didn't yet separate),
- When this story chooses the request/response schemas location,
- Then a NEW file `apps/api/app/modules/invite/admin_schemas.py` is added containing the three Pydantic schemas (named verbatim):
  - `GenerateInviteRequest` (request body for `POST /api/admin/invites` — `role: UserRole`, `ttl_preset: InviteTTLPreset | None = None`, `ttl_seconds: int | None = None`; mutual-exclusivity validated via `@model_validator(mode="after")`),
  - `GenerateInviteResponse` (response body for `POST /api/admin/invites` — `invite_id: uuid.UUID`, `token: str`, `registration_url: str`, `role: UserRole`, `ttl_seconds: int`, `expires_at: datetime.datetime`),
  - `InviteListItem` (one row inside `GET /api/admin/invites` items — `invite_id`, `role`, `ttl_seconds`, `generated_by_user_id`, `generated_at`, `expires_at`, `used_by_user_id`, `used_at`, `used_from_ip`, `revoked_at`, `status: Literal["active", "used", "expired", "revoked"]`),
  - `InviteListResponse` (response body for `GET /api/admin/invites` — `total: int`, `items: list[InviteListItem]`, `page: int`, `page_size: int`),
- And `apps/api/app/modules/invite/__init__.py` is UPDATED to re-export the four new schemas at module-package level so future modules (Story 6.4 register route, Story 8.6 admin UI's contract-typing) can import them as `from app.modules.invite import GenerateInviteRequest, ...`,
- And `apps/api/tests/test_invite_admin.py` (NEW file) contains AT LEAST the following test cases (verbatim names — checklist for the Dev Agent's TDD red-phase):
  - `test_generate_invite_requires_admin_cookie` — anonymous request → 401
  - `test_generate_invite_member_returns_403` — member cookie → 403
  - `test_generate_invite_returns_token_and_audit_row` — happy-path 201 + cleartext token + audit row
  - `test_generate_invite_with_ttl_preset_resolves_to_seconds` — `ttl_preset: "ONE_DAY"` → `ttl_seconds=86400` in response
  - `test_generate_invite_rejects_both_ttl_fields` — both supplied → 422
  - `test_generate_invite_rejects_neither_ttl_field` — neither supplied → 422
  - `test_generate_invite_rejects_agent_role` — `role="agent"` → 422 (router translates `ValueError` from service to 422)
  - `test_generate_invite_rejects_short_ttl_seconds` — `ttl_seconds=59` → 422
  - `test_generate_invite_rejects_long_ttl_seconds` — `ttl_seconds=7776001` → 422
  - `test_generate_invite_audit_payload_omits_cleartext_token` — explicit assertion `assert "token" not in audit.after` (token hygiene)
  - `test_generate_invite_csrf_header_required` — request without `X-Portal-Client` header → 403 `csrf_required`
  - `test_list_invites_requires_admin_cookie` — anonymous → 401
  - `test_list_invites_member_returns_403` — member cookie → 403
  - `test_list_invites_default_returns_all_statuses` — 4 seeded rows of varied status → 4 items + total=4
  - `test_list_invites_status_active_filters_correctly` — only the active row returned
  - `test_list_invites_status_used_filters_correctly` — only the used row
  - `test_list_invites_status_expired_filters_correctly` — only the expired row
  - `test_list_invites_status_revoked_filters_correctly` — only the revoked row
  - `test_list_invites_status_invalid_returns_422` — `?status=bogus` → 422
  - `test_list_invites_pagination_first_page` — `?page=1&page_size=2` → 2 items + total=N
  - `test_list_invites_pagination_beyond_last_page_returns_empty` — `?page=99` → 0 items + total=N (NOT 404)
  - `test_list_invites_pagination_page_size_upper_bound` — `?page_size=201` → 422
  - `test_list_invites_response_never_includes_cleartext_token` — explicit `assert "token" not in items[0] and "token_hash" not in items[0]`
  - `test_list_invites_ordering_is_generated_at_desc` — 3 rows with distinct `generated_at` values; assert ordering matches DESC
  - `test_revoke_invite_requires_admin_cookie` — anonymous → 401
  - `test_revoke_invite_member_returns_403` — member cookie → 403
  - `test_revoke_invite_happy_path_returns_204_and_audits` — 204 + `revoked_at` set + audit row
  - `test_revoke_invite_makes_token_unusable_via_service` — post-revoke `await service.validate_active(token)` returns `None`
  - `test_revoke_invite_nonexistent_id_returns_404` — random UUID → 404
  - `test_revoke_invite_already_used_returns_409` — pre-seeded `used_at IS NOT NULL` → 409
  - `test_revoke_invite_already_revoked_returns_409` — pre-seeded `revoked_at IS NOT NULL` → 409
  - `test_revoke_invite_csrf_header_required` — without header → 403 `csrf_required`
- And `pytest apps/api/tests/test_invite_admin.py -v` exits 0 with all the above tests green,
- And the full backend suite `pytest apps/api/` exits 0 with no regressions versus the Story 6.2 baseline (~452 tests; this story adds ~30+ → expected ~480+).

## Tasks / Subtasks

- [x] **T1 — Author `apps/api/app/modules/invite/admin_schemas.py` (AC-1, AC-2, AC-6)**
  - [x] T1.1 Create new file with the four Pydantic schemas listed in AC-6. Stdlib imports: `datetime`, `uuid`, `typing.Literal`. Pydantic: `BaseModel`, `ConfigDict`, `Field`, `model_validator`. Local: `from app.core.db.models._enums import UserRole`, `from app.modules.invite.models import InviteTTLPreset`.
  - [x] T1.2 `GenerateInviteRequest`: fields `role: UserRole`, `ttl_preset: InviteTTLPreset | None = None`, `ttl_seconds: int | None = None`. Use `model_config = ConfigDict(extra="forbid")` to reject typo'd keys (matches `sot/admin_schemas.py:42` `extra="forbid"` precedent for write payloads). Add a `@model_validator(mode="after")` that raises `ValueError("specify exactly one of ttl_preset, ttl_seconds")` when both are `None` OR both are non-`None`. Add a method `resolve_ttl_seconds(self) -> int`: returns `self.ttl_preset.value` if `ttl_preset is not None` else `self.ttl_seconds` (after the validator has guaranteed exactly-one). The router calls this method to obtain the int the service needs.
  - [x] T1.3 `GenerateInviteResponse`: fields `invite_id: uuid.UUID`, `token: str`, `registration_url: str`, `role: UserRole`, `ttl_seconds: int`, `expires_at: datetime.datetime`. `model_config = ConfigDict(frozen=True)` (response objects are immutable per share-module precedent).
  - [x] T1.4 `InviteListItem`: fields `invite_id: uuid.UUID`, `role: UserRole`, `ttl_seconds: int`, `generated_by_user_id: uuid.UUID | None`, `generated_at: datetime.datetime`, `expires_at: datetime.datetime`, `used_by_user_id: uuid.UUID | None`, `used_at: datetime.datetime | None`, `used_from_ip: str | None`, `revoked_at: datetime.datetime | None`, `status: Literal["active", "used", "expired", "revoked"]`. `model_config = ConfigDict(frozen=True)`. NO `token` / `token_hash` fields (hygiene per Decision B).
  - [x] T1.5 `InviteListResponse`: `total: int`, `items: list[InviteListItem]`, `page: int`, `page_size: int`. `model_config = ConfigDict(frozen=True)`.
  - [x] T1.6 Add a free function `derive_status(*, used_at, revoked_at, generated_at, ttl_seconds, now) -> Literal["active", "used", "expired", "revoked"]` that the router and tests can call to compute the derived status uniformly. Precedence: `revoked` (any `revoked_at`) > `used` (any `used_at IS NOT NULL` AND `revoked_at IS NULL`) > `expired` (no `used_at`, no `revoked_at`, but `generated_at + ttl_seconds <= now`) > `active`. Note the "revoked then used" combo is impossible per Decision A + Story 6.2 `consume()` predicate (used path requires `revoked_at IS NULL`), so the precedence is defensive only.

- [x] **T2 — Author `apps/api/app/modules/invite/admin_router.py` (AC-1, AC-3, AC-4, AC-5)**
  - [x] T2.1 RED — author the 6 generate-invite tests (`test_generate_invite_*`) from AC-6 against an empty router file. Tests use the existing `client` fixture pattern from `apps/api/tests/test_share_admin.py:14-67`: TestClient + `fakeredis.aioredis.FakeRedis()` swapped into `app.state.redis` + admin-JWT cookie minted via `encode_token(subject=str(user.id), role="admin", secret="test", ttl_minutes=30)`. Expected initial state: every test fails with HTTP 404 (route not registered).
  - [x] T2.2 GREEN — create `apps/api/app/modules/invite/admin_router.py` with the route + service factory + audit emission. Skeleton in Dev Notes § "Implementation skeleton — admin_router.py" below.
  - [x] T2.3 Wire `auth.invite.generated` audit emission. Follow the exact `record_event(get_engine(), action=..., entity_type="invite_token", entity_id=invite.id, actor_user_id=user_id, after={...}, request_id=request.headers.get("x-request-id"))` pattern from `share/admin_router.py:42-49`. The `after` payload contains `{"role": invite.role, "ttl_seconds": invite.ttl_seconds}`; explicitly NO `"token"` field (verified by `test_generate_invite_audit_payload_omits_cleartext_token`).
  - [x] T2.4 Run the 6 generate-invite tests; all should pass. Also run `test_generate_invite_csrf_header_required` (the global CSRF middleware already enforces — this test just verifies the middleware reaches the new route).

- [x] **T3 — Implement `GET /api/admin/invites` list endpoint with status filter + pagination (AC-2, AC-6)**
  - [x] T3.1 RED — author the 11 list-invites tests (`test_list_invites_*`) from AC-6 against the not-yet-written GET route.
  - [x] T3.2 GREEN — add the list handler. DB query: `select(InviteToken).order_by(InviteToken.generated_at.desc())`. For status filtering, build the WHERE clause via:
    - `active` → `used_at.is_(None) AND revoked_at.is_(None) AND (generated_at + interval ttl_seconds seconds > now)` — for SQLite use `generated_at > now - timedelta(seconds=ttl_seconds)` semantics; the cleanest implementation is to fetch all candidate rows where `used_at IS NULL AND revoked_at IS NULL` and filter the expiry in Python (the dataset is small — admin-bounded — and the index is on `generated_at`, not on a computed expiry, so a SQL `expires_at >` predicate would not benefit from indexing anyway). The Python-filter approach also handles the `expired` filter symmetrically.
    - `used` → `used_at.is_not(None) AND revoked_at.is_(None)` (DB predicate only — no Python filter needed)
    - `expired` → `used_at.is_(None) AND revoked_at.is_(None)` + Python filter `generated_at + ttl_seconds <= now`
    - `revoked` → `revoked_at.is_not(None)` (catches both revoked-then-never-used and revoked-after-used, though the latter is impossible per AC-3)
    - No filter → all rows
  - [x] T3.3 Pagination: take `page: int = Query(default=1, ge=1)` and `page_size: int = Query(default=50, ge=1, le=200)`. Compute `offset = (page - 1) * page_size`. `total` is `session.exec(select(func.count()).select_from(InviteToken).where(<same-where>)).one()` BEFORE the status-Python-filter, then adjust `total` by counting Python-filtered rows when status is `active` or `expired` (see Dev Notes § "List endpoint — pagination + computed-status interaction" for the binding rationale). The simpler-but-correct alternative is to load all matching rows, apply Python filter, then slice via `[offset:offset+page_size]` and `total = len(filtered_rows)` — given the admin-scoped dataset (≤O(100) active invites in steady state), this is the pragmatic choice and is what the binding implementation should use.
  - [x] T3.4 Per-row projection to `InviteListItem`: compute `expires_at = generated_at + timedelta(seconds=ttl_seconds)` and `status = derive_status(...)`; map FK / nullable columns directly. Strip `token_hash` (never project it — the field doesn't exist on `InviteListItem`).
  - [x] T3.5 Re-run the 11 list-invites tests; all green.

- [x] **T4 — Implement `POST /api/admin/invites/{id}/revoke` (AC-3, AC-4, AC-6)**
  - [x] T4.1 RED — author the 7 revoke tests (`test_revoke_invite_*`) from AC-6.
  - [x] T4.2 GREEN — add the revoke handler. Catch `InviteNotFound` → 404; `InviteAlreadyResolved` → 409. Use `try / except` around `await _service(request).revoke(invite_id)`. After a successful revoke, emit `auth.invite.revoked` audit row with `after={"invite_id": str(invite_id)}` and the same `request_id` header pattern. Return `Response(status_code=204)`.
  - [x] T4.3 Re-run the 7 revoke tests; all green.

- [x] **T5 — Wire router registration in `apps/api/app/router.py` + update `apps/api/app/modules/invite/__init__.py` re-exports (AC-5, AC-6)**
  - [x] T5.1 Edit `apps/api/app/router.py`: add `from app.modules.invite.admin_router import router as invite_admin_router` (alphabetical-by-module order between `auth_router` and `share_admin_router`). Add `api_router.include_router(invite_admin_router)` between `auth_router` and `sot_admin_router` (alphabetical-by-prefix `/api/admin/invites` lands between `/api/admin/` and `/api/admin/share` — see Dev Notes § "Router registration ordering" for the exact line-level placement).
  - [x] T5.2 Edit `apps/api/app/modules/invite/__init__.py`: add the four schema re-exports from `admin_schemas` (`GenerateInviteRequest`, `GenerateInviteResponse`, `InviteListItem`, `InviteListResponse`). Update `__all__` tuple in sorted order. Do NOT export the `derive_status` helper (private utility; importable directly if needed).
  - [x] T5.3 Verify the OpenAPI surface: `pytest apps/api/tests/test_runbook.py -k openapi` (the existing OpenAPI smoke gate) green; new endpoints appear in `/openapi.json` with the documented tags + response_model annotations.

- [x] **T6 — Final quality gate + status flip (all ACs)**
  - [x] T6.1 Run `pytest apps/api/tests/test_invite_admin.py -v` — all 30+ tests green.
  - [x] T6.2 Run `pytest apps/api/ -q` — full backend suite green (baseline 452; expected ~480+).
  - [x] T6.3 Run `ruff format apps/api/` + `ruff check apps/api/` — both clean. No `# noqa` exceptions.
  - [x] T6.4 Run `infra/scripts/check-all.sh` from repo root — all 10 stages green (matches the Story 6.2 close-out gate from `sprint-status.yaml` Sesja K note).
  - [x] T6.5 Update Dev Agent Record + File List below; flip `Status:` to `review`.

## Dev Notes

### Relevant architecture patterns and constraints

- **Init 0 share-admin precedent — copy the file shape AND the audit pattern.** The single canonical mental model for this story is `apps/api/app/modules/share/admin_router.py` (80 LOC, Init 0 pattern). Quick anatomy:
  - Module-level `router = APIRouter(prefix="/api/admin/share", tags=["admin", "share"])` — invite admin uses `prefix="/api/admin/invites", tags=["admin", "invite"]`.
  - `_service(request: Request) -> ShareService` factory at module top — invite admin uses an `_service()` factory returning `InviteService(redis=..., engine=...)` with the dual-backed constructor.
  - Route signatures use `user_id: uuid.UUID = current_admin` (default-value style, NOT `Depends(...)` body-resolution) — this style is consistent across every existing admin endpoint in the repo. NEW endpoints in this story MUST follow it.
  - Audit emission lives in the router (`record_event(get_engine(), action=..., entity_type="share_token", entity_id=None, actor_user_id=user_id, after={...})`), NOT in the service. Story 6.2's service explicitly delegates audit to the caller — this story is the caller; this is where `auth.invite.generated` + `auth.invite.revoked` get emitted.
  - `record_event()` is synchronous (commits its own audit session); calling it inside an async route function is fine (no `await`).

- **Decision A — dual-backed storage** (`architecture.md` §1417-1423 / Initiative 5): Redis is authoritative for "is this token currently consumable", DB is authoritative for "what happened with this token". For the LIST endpoint (AC-2), this is binding: **the list MUST query the DB, NOT Redis**. Decision A explicitly states "DB row outlives Redis TTL — used and expired invites remain visible in the admin panel forever; Redis only carries the active set." A Redis-based list would (correctly) show ONLY active invites; the admin Invites tab needs ALL rows including expired and revoked — so DB it is. The `ix_invite_tokens_generated_at` index from Story 6.1 supports the DESC ordering.

- **Decision B — token shape + admin-panel hygiene** (`architecture.md` §1425-1456): The cleartext token appears in TWO places only: (1) the one-time `POST /api/admin/invites` response (this story's AC-1), and (2) the `/register?token=` query string during consumption (Story 6.4's surface). The token MUST NOT appear in:
  - `GET /api/admin/invites` list response (AC-2 verifies this with explicit `assert "token" not in items[0]`)
  - `audit_log.after_json` (AC-1 + AC-3 verify this)
  - `audit_log.before_json` (never written — there's no "before" state for a fresh invite)
  - Any log line (the existing `TokenRedactionFilter` from Story 6.1 in `app/core/logging.py` is a defense-in-depth catch — the router code MUST NOT directly log the cleartext token in any form)
  - The DB row (Story 6.1's schema stores only `token_hash`, NOT the cleartext — no change this story)

- **Decision C — `current_admin` stays admin-only** (`architecture.md` §1458-1487): All three invite admin endpoints use `current_admin` (member returns 403 — AC-4 verifies). The new `current_member_or_admin` dependency lands in Story 6.5 for the `POST /api/share/` route ONLY. DO NOT confuse the two — every `/api/admin/*` route in the repo stays on `current_admin` per the per-route allowlist table.

- **FR5-INVITE-1 / FR5-INVITE-2 / FR5-INVITE-3 / FR5-AUDIT-1** are the four FRs this story realizes (per `epics.md` §1574 + the matching `prd.md` §1167-1170 + §1200 lines). The verifiable acceptance shapes are:
  - FR5-INVITE-1 (`prd.md:1167`): "an admin-generated token has 32-byte entropy; the matching DB row exists with `generated_by`, `generated_at`, `role`, `ttl_seconds` populated." → AC-1.
  - FR5-INVITE-2 (`prd.md:1168`): "filter applied; the row count and per-row metadata match the DB state." → AC-2.
  - FR5-INVITE-3 (`prd.md:1169`): "a `POST /api/admin/invites/{id}/revoke` followed by `GET /register?token=<that-token>` returns HTTP 410 Gone." → AC-3 (the `/register?token=` part lands in Story 6.4; this story verifies the equivalent at the service-layer level — `validate_active()` returns `None` after revoke — to keep Story 6.3 self-contained).
  - FR5-AUDIT-1 (`prd.md:1200`): the four `auth.invite.*` action names in `KNOWN_ENTITY_TYPES` (already registered by Story 6.1); this story emits two of them (`auth.invite.generated`, `auth.invite.revoked`). The third (`auth.invite.used`) is Story 6.4's responsibility. The fourth (`auth.register.*`) is also Story 6.4.

- **`X-Portal-Client: web` CSRF middleware** (`app/core/auth/csrf.py`): GLOBAL middleware that returns 403 `csrf_required` for any unsafe-method `/api/...` request (except `/api/share/*`) that lacks the `X-Portal-Client: web` header. The conftest `client` fixture at `apps/api/tests/conftest.py:64` sets this header by default. AC-3 + AC-6 include explicit "CSRF header required" tests that strip the header to verify the middleware reaches the new routes. **No new middleware code needed in this story** — the existing global middleware covers the new prefix automatically.

- **No new dependencies.** Pydantic, sqlmodel, redis, sqlalchemy, fakeredis are all already in `pyproject.toml`. The new files use stdlib-only imports plus the existing repo dependencies.

- **`__init__.py` re-export discipline.** Story 6.2 established the pattern: all public surface is re-exported from `apps/api/app/modules/invite/__init__.py` so callers do `from app.modules.invite import X` rather than `from app.modules.invite.service import X`. This story extends `__init__.py` with the four schema names; the `__all__` tuple stays sorted (ruff's `isort` rule enforces this).

### Implementation skeleton — admin_router.py (binding for shape)

```python
"""Admin endpoints for invite-token lifecycle (Initiative 5 Story 6.3).

Mirrors the Init 0 share-admin shape in
``apps/api/app/modules/share/admin_router.py`` with the same conventions:
- ``_service(request)`` factory builds the InviteService per request,
- ``current_admin`` dependency on every route,
- ``record_event()`` emission in the router (NOT the service),
- FastAPI default ``{"detail": "..."}`` error envelope.

Audit actions emitted:
- ``auth.invite.generated`` on POST /api/admin/invites (201)
- ``auth.invite.revoked``  on POST /api/admin/invites/{id}/revoke (204)
"""

import datetime
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlmodel import Session, func, select

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.db.session import get_engine, get_session
from app.modules.invite import (
    GenerateInviteRequest,
    GenerateInviteResponse,
    InviteAlreadyResolved,
    InviteListItem,
    InviteListResponse,
    InviteNotFound,
    InviteService,
    InviteToken,
)
from app.modules.invite.admin_schemas import derive_status

router = APIRouter(prefix="/api/admin/invites", tags=["admin", "invite"])


def _service(request: Request) -> InviteService:
    return InviteService(redis=request.app.state.redis.get(), engine=get_engine())


@router.post("", status_code=201, response_model=GenerateInviteResponse)
async def generate_invite(
    payload: GenerateInviteRequest,
    request: Request,
    user_id: uuid.UUID = current_admin,
) -> GenerateInviteResponse:
    ttl_seconds = payload.resolve_ttl_seconds()
    try:
        result = await _service(request).generate_invite(
            role=payload.role,
            ttl_seconds=ttl_seconds,
            generated_by_user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    invite = result.invite
    expires_at = invite.generated_at + datetime.timedelta(seconds=invite.ttl_seconds)
    record_event(
        get_engine(),
        action="auth.invite.generated",
        entity_type="invite_token",
        entity_id=invite.id,
        actor_user_id=user_id,
        after={"role": invite.role, "ttl_seconds": invite.ttl_seconds},
        request_id=request.headers.get("x-request-id"),
    )
    return GenerateInviteResponse(
        invite_id=invite.id,
        token=result.token,
        registration_url=f"/register?token={result.token}",
        role=invite.role,
        ttl_seconds=invite.ttl_seconds,
        expires_at=expires_at,
    )


@router.get("", response_model=InviteListResponse)
async def list_invites(
    session: Annotated[Session, Depends(get_session)],
    status_filter: Literal["active", "used", "expired", "revoked"] | None = Query(
        default=None, alias="status"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _user_id: uuid.UUID = current_admin,
) -> InviteListResponse:
    now = datetime.datetime.now(datetime.UTC)
    rows = session.exec(
        select(InviteToken).order_by(InviteToken.generated_at.desc())
    ).all()
    items = []
    for row in rows:
        item_status = derive_status(
            used_at=row.used_at,
            revoked_at=row.revoked_at,
            generated_at=row.generated_at,
            ttl_seconds=row.ttl_seconds,
            now=now,
        )
        if status_filter is not None and item_status != status_filter:
            continue
        items.append(
            InviteListItem(
                invite_id=row.id,
                role=row.role,
                ttl_seconds=row.ttl_seconds,
                generated_by_user_id=row.generated_by_user_id,
                generated_at=row.generated_at,
                expires_at=row.generated_at + datetime.timedelta(seconds=row.ttl_seconds),
                used_by_user_id=row.used_by_user_id,
                used_at=row.used_at,
                used_from_ip=row.used_from_ip,
                revoked_at=row.revoked_at,
                status=item_status,
            )
        )
    total = len(items)
    offset = (page - 1) * page_size
    sliced = items[offset : offset + page_size]
    return InviteListResponse(total=total, items=sliced, page=page, page_size=page_size)


@router.post("/{invite_id}/revoke", status_code=204)
async def revoke_invite(
    invite_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = current_admin,
) -> Response:
    try:
        await _service(request).revoke(invite_id)
    except InviteNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "invite not found") from exc
    except InviteAlreadyResolved as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "invite already used or revoked"
        ) from exc
    record_event(
        get_engine(),
        action="auth.invite.revoked",
        entity_type="invite_token",
        entity_id=invite_id,
        actor_user_id=user_id,
        after={"invite_id": str(invite_id)},
        request_id=request.headers.get("x-request-id"),
    )
    return Response(status_code=204)
```

This skeleton is binding for shape — small variations (logging additions, docstring polish, helper extraction) are fine; structural deviations (e.g. service-layer record_event calls, swapping `current_admin` for `current_user`, emitting cleartext token in the audit `after`, exposing a `token` field on `InviteListItem`) require a `bmad-correct-course` pass on this spec.

### Implementation skeleton — admin_schemas.py (binding for shape)

```python
"""Request/response schemas for the Initiative 5 invite-token admin router.

Kept separate from ``models.py`` (which holds the SQLModel + helpers) for
parity with ``sot/admin_schemas.py`` (Init 2 SoT pattern) — every admin
write/read surface in the repo isolates its Pydantic schemas in a
dedicated module so the SQLModel + Pydantic concerns stay independent.

Hygiene rule: NONE of these schemas expose the cleartext token field
other than ``GenerateInviteResponse``. Decision B (architecture.md
§1425-1456) is binding: cleartext token surfaces once, at generation.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.db.models._enums import UserRole
from app.modules.invite.models import InviteTTLPreset

StatusLiteral = Literal["active", "used", "expired", "revoked"]


class GenerateInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: UserRole
    ttl_preset: InviteTTLPreset | None = None
    ttl_seconds: int | None = Field(default=None, ge=60, le=7776000)

    @model_validator(mode="after")
    def _exactly_one_ttl(self) -> "GenerateInviteRequest":
        if (self.ttl_preset is None) == (self.ttl_seconds is None):
            raise ValueError("specify exactly one of ttl_preset, ttl_seconds")
        return self

    def resolve_ttl_seconds(self) -> int:
        if self.ttl_preset is not None:
            return self.ttl_preset.value
        assert self.ttl_seconds is not None  # validated above
        return self.ttl_seconds


class GenerateInviteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    invite_id: uuid.UUID
    token: str
    registration_url: str
    role: UserRole
    ttl_seconds: int
    expires_at: datetime.datetime


class InviteListItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    invite_id: uuid.UUID
    role: UserRole
    ttl_seconds: int
    generated_by_user_id: uuid.UUID | None
    generated_at: datetime.datetime
    expires_at: datetime.datetime
    used_by_user_id: uuid.UUID | None
    used_at: datetime.datetime | None
    used_from_ip: str | None
    revoked_at: datetime.datetime | None
    status: StatusLiteral


class InviteListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    total: int
    items: list[InviteListItem]
    page: int
    page_size: int


def derive_status(
    *,
    used_at: datetime.datetime | None,
    revoked_at: datetime.datetime | None,
    generated_at: datetime.datetime,
    ttl_seconds: int,
    now: datetime.datetime,
) -> StatusLiteral:
    """Compute derived status uniformly. Precedence: revoked > used > expired > active."""
    if revoked_at is not None:
        return "revoked"
    if used_at is not None:
        return "used"
    if generated_at + datetime.timedelta(seconds=ttl_seconds) <= now:
        return "expired"
    return "active"
```

Schema note — `UserRole` Pydantic-serialization: `UserRole` is a `StrEnum` (per the corrected Story 6.1 spec § Drift 4 + the actual code in `apps/api/app/core/db/models/_enums.py`). Pydantic serializes StrEnum values as their string form by default, so `role: UserRole` fields appear as `"member"` / `"admin"` in JSON responses without extra config. No `use_enum_values=True` needed.

### List endpoint — pagination + computed-status interaction (binding rationale)

The list endpoint's pagination semantics interact with the computed `status` field in a subtle way that future maintainers will need to understand:

- `active` and `expired` are computed in Python (the `now > generated_at + ttl_seconds` check is not a DB predicate — see Decision A "Redis only carries the active set; DB has all rows"). This means the DB query SHOULD NOT push the status filter through SQL — it should fetch all candidate rows (matching `used_at IS NULL AND revoked_at IS NULL` for active/expired; matching `used_at IS NOT NULL AND revoked_at IS NULL` for used; matching `revoked_at IS NOT NULL` for revoked) and let Python compute the final status + filter.
- The pragmatic choice for Story 6.3 is to fetch all rows from `invite_tokens` (no DB WHERE on status), compute `derive_status` per row, filter by `status_filter` in Python, then slice for pagination. The dataset is admin-bounded — even if Init 5 runs for 5 years, the row count stays in the O(thousands) range, well within in-process Python filtering capacity (10k rows × ~10 fields → ~100KB working set).
- A future Story (NOT this one) could optimize via a DB-side computed `status` column or a materialized-view, but that's out-of-scope for the MVP. Document the trade-off in a one-line code comment near `select(InviteToken).order_by(...)` so the next maintainer doesn't "fix" it without context.

### Router registration ordering (binding placement)

`apps/api/app/router.py` currently has the include_router calls in this order (matches alphabetical-by-module-name within their groupings):

```python
api_router.include_router(auth_router)
api_router.include_router(sot_admin_router)
api_router.include_router(admin_router)
api_router.include_router(share_admin_router)
api_router.include_router(share_router)
api_router.include_router(sot_router)
```

The binding placement for `invite_admin_router` is **between `auth_router` and `sot_admin_router`** — alphabetical-by-module-name (`auth` < `invite` < `share` < `sot`). The new `from ... import` statement at the top should follow the same alphabetical order: after `auth_router` import, before `share_admin_router`. The future `invite_router` (Story 6.4's public `/api/auth/register?token=` route lives in `auth/router.py`, not a new file, so this story doesn't need to provision for an invite-side `router.py`) — Story 6.4 lands its endpoint inside the existing auth router.

NOTE: the existing router.py file has `sot_admin_router` and `admin_router` ordering that looks non-alphabetical (sot first, then admin). Two readings: (a) FastAPI's `include_router` is order-independent for routing (each path is unique), so the order doesn't matter functionally; (b) the existing arrangement looks like it grew organically rather than being intentionally ordered. Story 6.3 should place `invite_admin_router` alphabetically (after auth, before sot/admin) for consistency, but the order won't affect behaviour. If the dev agent observes that fix-ordering would be a separable cleanup, escalate as a triage candidate per `feedback_preexisting_issue_threshold.md` (single-story flag → wait for the 3rd flag before promoting).

### `request_id` propagation note

Audit rows include a `request_id` field. The existing routers fetch it via `request.headers.get("x-request-id")` (see `share/admin_router.py:42` does NOT pass `request_id` — let me re-verify: it omits `request_id` entirely; `sot/admin_router.py:357 / 413 / 476` DOES pass `request_id=request.headers.get("x-request-id")`). The binding choice for this story: **DO pass `request_id`** in both `record_event()` calls — mirrors the SoT-router pattern (which is the newer + more consistent approach), and surfaces the X-Request-Id trace tag in audit queries for E9 audit observability per NFR5-OBS-1. The share-router omission is legacy; do NOT propagate that omission to new code.

### Source tree components to touch

**NEW files:**

- [apps/api/app/modules/invite/admin_router.py](../../apps/api/app/modules/invite/admin_router.py) — three endpoints (`POST` generate / `GET` list / `POST /{id}/revoke`) + `_service()` factory. Expected size: ~120-150 LOC including docstrings + import block.
- [apps/api/app/modules/invite/admin_schemas.py](../../apps/api/app/modules/invite/admin_schemas.py) — four Pydantic schemas + `derive_status()` helper. Expected size: ~80-100 LOC.
- [apps/api/tests/test_invite_admin.py](../../apps/api/tests/test_invite_admin.py) — 30+ tests from AC-6 enumeration. Expected size: ~500-700 LOC using the `test_share_admin.py` fixture pattern as template. Test data setup: seed 4 invite rows via direct `Session.add(InviteToken(...))` calls (NOT through the service — tests at this layer exercise the HTTP surface, the service layer is verified in `test_invite_service.py` from Story 6.2).

**UPDATE files:**

- [apps/api/app/modules/invite/__init__.py](../../apps/api/app/modules/invite/__init__.py) — add `from app.modules.invite.admin_schemas import GenerateInviteRequest, GenerateInviteResponse, InviteListItem, InviteListResponse` + the four names into the sorted `__all__` tuple. Keep the existing 10 re-exports unchanged.
- [apps/api/app/router.py](../../apps/api/app/router.py) — add `from app.modules.invite.admin_router import router as invite_admin_router` + `api_router.include_router(invite_admin_router)` (alphabetical placement per "Router registration ordering" above).

**NO changes:**

- `apps/api/app/modules/invite/service.py` — Story 6.2's service is complete. DO NOT modify. The router catches `ValueError` / `InviteNotFound` / `InviteAlreadyResolved` from the existing service; the existing exception hierarchy is sufficient.
- `apps/api/app/modules/invite/models.py` — Story 6.1's SQLModel is correct as-is. DO NOT add new columns.
- `apps/api/app/core/auth/dependencies.py` — `current_admin` is sufficient. The new `current_member_or_admin` dependency lands in Story 6.5, not this one.
- `apps/api/app/core/auth/csrf.py` — global CSRF middleware already covers `/api/admin/invites` (the new prefix matches the `path.startswith("/api/")` guard).
- `apps/api/app/core/audit.py` — `"invite_token"` already in `KNOWN_ENTITY_TYPES` (Story 6.1). No edits.
- `apps/api/app/core/logging.py` — `TokenRedactionFilter` in place; do NOT log cleartext token in the new router (per Decision B hygiene rule).
- `apps/api/app/main.py` — no lifespan-startup edits; `app.state.redis` + `get_engine()` already wired.
- `apps/api/pyproject.toml` — no new dependencies.

### Testing standards summary

- **Fixture pattern:** copy `apps/api/tests/test_share_admin.py:14-67` verbatim (with `tmp_path` + `monkeypatch` env setup + `fakeredis` injection + admin-JWT cookie minting). The conftest `_isolated_db` autouse fixture provides the DB schema; the test's per-file `client` fixture provides the TestClient + Redis swap + admin user UUID + admin JWT.
- **Member JWT for 403 tests:** mint via `encode_token(subject=<member_uuid>, role="member", secret="test", ttl_minutes=30)` — the member user does NOT need to exist in the `user` table for the dependency to reject the request (the role check fires on the JWT claim, not on a DB lookup). For tests that need an actual member row (none in this story), seed one via `User(..., role=UserRole.member, ...)` direct insert.
- **CSRF tests:** to verify the global middleware's reach to the new routes, override the conftest header via `c.headers.pop("X-Portal-Client", None)` BEFORE issuing the request; the middleware returns 403 `csrf_required` and no audit row is written.
- **Audit-row assertions:** after each happy-path test, query `select(AuditLog).where(AuditLog.action == "auth.invite.generated")` (or `.revoked`) to confirm the row exists with the expected fields. Use a fresh session, NOT the test client's session.
- **`fake_redis` cleanup:** `fakeredis.aioredis.FakeRedis()` per the `client` fixture is per-test (new instance each test) — Redis-side isolation is automatic. The DB-side isolation needs care: the session-scope `_isolated_db` fixture provides a single SQLite file for ALL tests, so each test MUST clean up its own `invite_tokens` rows. Use an autouse fixture at top of `test_invite_admin.py`:
  ```python
  @pytest.fixture(autouse=True)
  def _clear_invite_and_audit_tables():
      from app.core.db.models import AuditLog
      from app.core.db.session import get_engine
      from app.modules.invite import InviteToken
      with Session(get_engine()) as s:
          for row in s.exec(select(InviteToken)).all():
              s.delete(row)
          for row in s.exec(select(AuditLog)).all():
              s.delete(row)
          s.commit()
      yield
  ```
  Note this autouse fixture also clears `audit_log` rows between tests so each test's audit-assertion sees only its own emissions.
- **TDD discipline:** RED → GREEN → REFACTOR per task. Within T2/T3/T4, author the failing tests FIRST (all should fail with 404 / 422 / ImportError until the route + schemas land), then implement, then verify all task tests pass before moving on.
- **Ruff config:** repo's `pyproject.toml` enforces `["E", "F", "W", "I", "B", "UP", "SIM", "RUF"]` with `line-length = 100`. The new files MUST pass `ruff format` + `ruff check` clean.
- **No `# noqa`.** If the linter complains, fix the code.
- **Quality gate:** `infra/scripts/check-all.sh` end-of-story.

### Project Structure Notes — alignment with unified structure + detected variances

- **Path alignment:** the module path `apps/api/app/modules/invite/admin_router.py` is the canonical filename per `_bmad-output/project-context.md` rule "Backend modules live in `apps/api/app/modules/<feature>/{router.py,service.py,admin_router.py,models.py}`". The new `admin_schemas.py` is an additional file (precedent: `sot/admin_schemas.py`); not in the canonical 4-file list but doesn't conflict.
- **`__all__` sort order in `__init__.py`:** ruff's `RUF022` rule enforces alphabetical sorting of `__all__` tuples. Story 6.2 already sorted the existing 10 names; the four new names (`GenerateInviteRequest`, `GenerateInviteResponse`, `InviteListItem`, `InviteListResponse`) slot in alphabetically. The Story 6.2 spec called out this lint gotcha explicitly — DO NOT skip the sort.
- **No new conventions introduced.** This story strictly follows Init 0 + Init 2 admin-router patterns. The only novel element is the `derive_status` helper, which is module-local utility (private to admin_schemas.py); no abstraction layer added.
- **Drift carry-over from Stories 6.1 + 6.2:** all four planning-doc drifts (path / KNOWN_ENTITY_TYPES / UUID / UserRole naming) are code-applied. This spec uses the corrected forms (`apps/api/migrations/versions/`, `"invite_token"` entity_type, UUID PKs, `UserRole.member`/`admin`). The planning artifacts (epics.md, prd.md, architecture.md) still carry original wording in places — a future `bmad-correct-course` patch is optional, NOT blocking.

### References

- [_bmad-output/planning-artifacts/epics.md § Initiative 5 Story 6.3](../planning-artifacts/epics.md) — lines 1572-1585. Binding scope source (5 acceptance bullets covering generate / list / revoke / current_admin guard / Init 0 conventions).
- [_bmad-output/planning-artifacts/epics.md § Epic 6 acceptance gate](../planning-artifacts/epics.md) — line 1537. End-to-end happy path: "invite generated by admin via Story 6.3 endpoint → consumed via Story 6.4 register flow → ... All E6 audit actions ... visible via `/api/admin/audit`". This story owns the FIRST link in that chain.
- [_bmad-output/planning-artifacts/prd.md § Initiative 5 FR5-INVITE-1](../planning-artifacts/prd.md) — line 1167. "Admin can generate single-use invite tokens" + verifiable acceptance shape.
- [_bmad-output/planning-artifacts/prd.md § Initiative 5 FR5-INVITE-2](../planning-artifacts/prd.md) — line 1168. List filter + per-row metadata contract.
- [_bmad-output/planning-artifacts/prd.md § Initiative 5 FR5-INVITE-3](../planning-artifacts/prd.md) — line 1169. Immediate revoke + downstream 410 on `/register?token=` (Story 6.4 surface).
- [_bmad-output/planning-artifacts/prd.md § Initiative 5 FR5-AUDIT-1](../planning-artifacts/prd.md) — line 1200. The 16 audit-log actions registered in `KNOWN_ENTITY_TYPES`; this story emits two (`auth.invite.generated`, `auth.invite.revoked`).
- [_bmad-output/planning-artifacts/architecture.md § Initiative 5 Decision A](../planning-artifacts/architecture.md) — lines 1417-1423. Dual-backed storage authority — admin list queries DB, not Redis.
- [_bmad-output/planning-artifacts/architecture.md § Initiative 5 Decision B](../planning-artifacts/architecture.md) — lines 1425-1456. Token shape + TTL bounds + `InviteTTLPreset` enum + admin-panel hygiene ("cleartext token never returned in any list-invites response").
- [_bmad-output/planning-artifacts/architecture.md § Initiative 5 Decision C](../planning-artifacts/architecture.md) — lines 1458-1487. Per-route allowlist table — `/api/admin/*` stays on `current_admin`.
- [_bmad-output/implementation-artifacts/6-1-alembic-0012-invite-tokens-primitives.md](6-1-alembic-0012-invite-tokens-primitives.md) — Story 6.1 spec. The `invite_tokens` schema + `KNOWN_ENTITY_TYPES += "invite_token"` + `TokenRedactionFilter` are pre-existing.
- [_bmad-output/implementation-artifacts/6-2-invite-service-dual-backed-crud.md](6-2-invite-service-dual-backed-crud.md) — Story 6.2 spec. The `InviteService` four-method contract + exception hierarchy + `__init__.py` re-export pattern this story builds on.
- [apps/api/app/modules/share/admin_router.py](../../apps/api/app/modules/share/admin_router.py) — Init 0 share-admin endpoints, 80 LOC. Canonical mental model for shape (`_service()` factory + `current_admin` parameter style + `record_event()` post-action emission + 201/204 status codes).
- [apps/api/app/modules/sot/admin_router.py](../../apps/api/app/modules/sot/admin_router.py) — Init 2 SoT-admin endpoints, 1076 LOC. Canonical reference for `request_id=request.headers.get("x-request-id")` propagation pattern (lines 357 / 413 / 476). The binding pattern for new code is the SoT one (DO pass `request_id`), not the share-router omission.
- [apps/api/app/modules/sot/admin_schemas.py](../../apps/api/app/modules/sot/admin_schemas.py) — Init 2 schema-isolation pattern. Reference for the dedicated `admin_schemas.py` file layout + `extra="forbid"` + `ConfigDict(json_schema_extra={"examples": [...]})` + `@model_validator` precedent.
- [apps/api/app/modules/share/models.py](../../apps/api/app/modules/share/models.py) — Init 0 share schemas (request + response Pydantic in same module). NOT the chosen pattern for this story (we use the SoT-style separation), but useful reference for `CreateShareResponse` shape vs `GenerateInviteResponse`.
- [apps/api/app/modules/invite/service.py](../../apps/api/app/modules/invite/service.py) — Story 6.2's `InviteService` + exceptions. The caller contract this story consumes.
- [apps/api/app/modules/invite/models.py](../../apps/api/app/modules/invite/models.py) — Story 6.1's `InviteToken` SQLModel + `InviteTTLPreset(IntEnum)` + `hash_token` helper. No edits.
- [apps/api/app/modules/invite/__init__.py](../../apps/api/app/modules/invite/__init__.py) — Story 6.2's 10-name re-export. This story adds 4 more.
- [apps/api/app/router.py](../../apps/api/app/router.py) — central include_router aggregation. One-line addition.
- [apps/api/app/core/auth/dependencies.py](../../apps/api/app/core/auth/dependencies.py) — `current_admin` dependency. The 403 envelope is `{"detail": "admin_required"}` (line 30).
- [apps/api/app/core/auth/csrf.py](../../apps/api/app/core/auth/csrf.py) — global CSRF middleware. The 403 envelope is `{"detail": "csrf_required"}` (line 19). New routes are covered automatically.
- [apps/api/app/core/audit.py](../../apps/api/app/core/audit.py) — `record_event()` signature + `KNOWN_ENTITY_TYPES` registry. `"invite_token"` already registered (Story 6.1, commit `6315d84`).
- [apps/api/tests/test_share_admin.py](../../apps/api/tests/test_share_admin.py) — 125 LOC, Init 0 admin-router test pattern. Direct template for `test_invite_admin.py` fixture shape + auth-cookie minting + role-assertion structure.
- [apps/api/tests/test_audit.py](../../apps/api/tests/test_audit.py) — `test_record_event_accepts_invite_token_entity_type` (lines 85-119). Verifies `"invite_token"` is accepted by `record_event()`. Read-only reference; no changes this story.
- [apps/api/tests/conftest.py](../../apps/api/tests/conftest.py) — `_isolated_db` autouse fixture + `_patch_arq_pool` + `client` fixture. The new test file reuses all three.

### Previous-story intelligence (6.1 + 6.2 → 6.3 carry-over)

**From Story 6.1 (commit `6315d84` + fix-up `4ed620d`):**
- The `invite_tokens` schema is fixed (10 columns + 3 indexes). DO NOT propose new columns or re-issue the migration.
- `KNOWN_ENTITY_TYPES += "invite_token"` is in place; `record_event(action="auth.invite.generated", entity_type="invite_token", ...)` is the ready-to-call shape.
- `TokenRedactionFilter` in `apps/api/app/core/logging.py` redacts cleartext tokens in stdout — defense-in-depth catch. The new router MUST NOT actively log cleartext tokens; the filter only catches accidental leakage.
- The Alembic chain is at `0012_invite_tokens` on `.190`. Story 6.3 makes no Alembic changes.

**From Story 6.2 (commit `8944669` + fix-up `82ef441`):**
- `InviteService` has the four async methods with the exact signatures used in the skeleton above. `generate_invite()` raises `ValueError` for bad role/TTL → router translates to 422. `revoke()` raises `InviteNotFound` → 404 + `InviteAlreadyResolved` → 409. `consume()` raises `InviteConsumed` (which this story does NOT exercise — that's Story 6.4's surface).
- Story 6.2's `revoke()` already does the SCAN-based Redis key DEL + DB-side CAS predicate `WHERE used_at IS NULL AND revoked_at IS NULL` (the CAS shipped in fix-up `82ef441`). This story relies on those properties; do NOT reimplement.
- Story 6.2's `__init__.py` re-exports `InviteService`, the 4 exceptions, `GenerateInviteResult`, `ActiveInvite`, `InviteToken`, `InviteTTLPreset`, `hash_token` — 10 names total. This story extends with 4 more from `admin_schemas`.
- The `_seed_users_and_clear_invites` autouse fixture in `test_invite_service.py` seeds 3 user rows for FK satisfaction — this story's `test_invite_admin.py` does NOT need to copy that fixture verbatim; the `client` fixture from `test_share_admin.py` already mints an admin user row via the existing `_isolated_db` schema-init path. If a test wants `generated_by_user_id` populated on an `InviteToken` row inserted directly (bypassing the service), it needs to either reuse the admin row's UUID or seed a member row first — the autouse fixture in this story's test file handles the seeding.

**From Story 6.1's Codex review (commit `4ed620d`):**
- The `TokenRedactionFilter` was hardened to redact tokens from BOTH `record.msg` AND structured pass-through fields. The hardening means future routers that log token-bearing dicts are also covered — but defense-in-depth is not an excuse to log tokens deliberately.

### Git intelligence summary

Last 5 commits on `main` (`git log --oneline -5`):

- `82ef441 fix(api): Story 6.2 codex review fix-up — atomic revoke (CAS predicate)` — 2026-05-19. Hardened `revoke()` to use `UPDATE ... WHERE used_at IS NULL AND revoked_at IS NULL` (CAS predicate) instead of a read-modify-write pattern. Story 6.3 inherits this CAS-on-revoke; the 409 path triggers when CAS finds zero rows. **Do not regress this property** — the router catches `InviteAlreadyResolved` and that exception ONLY fires from the CAS predicate matching zero rows.
- `8944669 feat(api): invite service dual-backed write/read/revoke/consume (Story 6.2)` — the dev commit for Story 6.2.
- `4ed620d fix(api): Story 6.1 codex review fix-up (logging redaction + init_schema)` — Story 6.1 fix-up.
- `4230195 docs(agents): self-triggering refinement to autonomous development mode` — doc-only.
- `6315d84 feat(api): alembic 0012_invite_tokens + invite primitives (Story 6.1)` — Story 6.1 dev commit.

The repo state for Story 6.3 development is stable: no in-flight backend feature work, no Alembic surface in transit, no Redis topology changes. Story 6.3 lands on a quiescent `apps/api/` tree after Story 6.2 close-out. The check-all.sh quality gate (commit `7787d52`) is in place.

### Latest technical specifics

- **FastAPI 0.115.x / 0.116.x range** (verify via `apps/api/pyproject.toml`): the `Annotated[X, Query(...)]` + `Annotated[Session, Depends(get_session)]` patterns used in the skeleton above are the modern idiom. The older `Query(..., regex=...)` parameter is deprecated in favor of `Query(..., pattern=...)`; the skeleton doesn't use regex. The `Literal["active", ...]` query param type triggers FastAPI's automatic enum validation, returning 422 for unknown values — no manual validation code needed.
- **Pydantic 2.x** (in use across the repo): `model_validator(mode="after")` is the modern decorator; `ConfigDict(frozen=True)` is the v2 way to declare immutability; `ConfigDict(extra="forbid")` rejects unknown keys at validation time. The `@model_validator(mode="after")` returns `self` (NOT the cls) for v2 compatibility.
- **`UserRole` enum import path:** `from app.core.db.models._enums import UserRole`. NOT `from app.core.db.models import UserRole` directly (it IS re-exported from the `__init__.py` per `models/__init__.py:34 + 57` — both paths work, but the underscore-prefixed `_enums` import keeps the dependency contract narrow). The skeleton uses the explicit path.
- **SQLAlchemy `func.count()` for pagination total:** when status filter pushes through Python (the binding choice for this story), the `total` count is `len(filtered_rows)` post-Python-filter — no SQL count needed.

### Audit-event hygiene contract (binding for this story)

The two `record_event()` calls in this story MUST satisfy:

- `auth.invite.generated`:
  - `entity_type="invite_token"`
  - `entity_id=invite.id` (the just-created row's UUID — NOT `None`; tied to the per-row resource)
  - `actor_user_id=user_id` (the admin's UUID from the cookie)
  - `request_id=request.headers.get("x-request-id")` (matches SoT pattern; may be `None` if header absent)
  - `after={"role": invite.role, "ttl_seconds": invite.ttl_seconds}` — NO `"token"` field, NO `"token_hash"` field, NO `"registration_url"` field (that's response-only)
  - `before=None` (no previous state for a fresh invite)
- `auth.invite.revoked`:
  - `entity_type="invite_token"`
  - `entity_id=invite_id` (path param)
  - `actor_user_id=user_id`
  - `request_id=request.headers.get("x-request-id")`
  - `after={"invite_id": str(invite_id)}` — minimal payload; the audit grain is "admin X revoked invite Y at time Z", details available in the DB row
  - `before=None` (or optionally a small dict capturing pre-revoke status — but keep it minimal; the audit table is for "what action ran", the `invite_tokens` row is the canonical state record)

If a future requirement adds more fields to the audit payload (e.g. recipient email for issued invites once OOB delivery channels are tracked — out of scope for E6), update this hygiene contract in lockstep. NO field MAY include cleartext token at any future date — that's a Decision B invariant.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Claude Code Opus 4.7 1M ctx)

### Debug Log References

- Pierwszy run pełnego suite: `test_generate_invite_with_ttl_preset_resolves_to_seconds` zwracał 422 zamiast 201 — przyczyna: `InviteTTLPreset` to `IntEnum`, więc Pydantic domyślnie oczekuje wartości liczbowej, a AC-1 wiąże API contract do string-name (`"ONE_DAY"`). Dodany `@field_validator("ttl_preset", mode="before")` mapuje string-name na enum member przez `InviteTTLPreset[v]`.
- `test_revoke_invite_makes_token_unusable_via_service` początkowo wybuchał `RuntimeError: Queue ... is bound to a different event loop` — przyczyna: `fakeredis.aioredis.FakeRedis` jest powiązany z event-loopem TestClient'a, a próba uruchomienia korutyny na nowym loopie konfliktuje z fakeredis internalami. Rozwiązanie: użyć `c.portal.call(...)` (Starlette TestClient utrzymuje anyio blocking portal do loopa fixture'a).
- `test_openapi_agent_surface.py::test_every_admin_sot_operation_has_description` faili dla nowych endpointów — gate wymagała non-empty `description` dla każdej operacji z tagiem `admin`. Dodane `summary` + `description` do trzech endpointów (precedent: `sot/admin_router.py`).
- Ruff RUF059 dla `fake_redis` unpacked-but-unused w dwóch testach → prefiks `_fake_redis`. Ruff F401 dla nieużywanego importu `UserRole` w teście → usunięty.

### Completion Notes List

- AC-1 (generate): POST `/api/admin/invites` zwraca 201 + cleartext token tylko w response body. Audit row `auth.invite.generated` ma `entity_id=invite.id`, `actor_user_id=admin_uuid`, `after={"role", "ttl_seconds"}` — bez `token`/`token_hash`/`registration_url` (Decision B hygiene).
- AC-2 (list): GET `/api/admin/invites` zwraca DB rows posortowane `generated_at DESC`, status computed Python-side (`derive_status` helper), pagination 1-indexed z `page_size ∈ [1, 200]`. Cleartext token nigdy w response (assert w testach).
- AC-3 (revoke): POST `/api/admin/invites/{id}/revoke` → 204, 404 dla nieistniejącego, 409 dla already-used/revoked (przez catch `InviteNotFound`/`InviteAlreadyResolved` z Story 6.2 service). Audit row `auth.invite.revoked` z `entity_id=invite_id`, payload `{"invite_id"}` bez tokena.
- AC-4 (auth): wszystkie trzy endpointy używają `current_admin` — member cookie → 403 `admin_required`, anonim → 401 `missing_access`. Global CSRF middleware sięga nowego prefixu (testy strip'ujące `X-Portal-Client` zwracają 403 `csrf_required`).
- AC-5 (conventions): `_service()` factory, `current_admin` dependency, `record_event()` emisja w routerze (NIE w service), FastAPI default error envelope `{"detail": ...}`, `user_id: uuid.UUID = current_admin` parameter style, `request_id=request.headers.get("x-request-id")` propagacja (zgodna z SoT pattern, nie share legacy). Ruff format + check czysto.
- AC-6 (schemas + tests): `admin_schemas.py` z 4 schemami + `derive_status` helper. `__init__.py` re-exports rozszerzone z 10 → 14 nazw (sorted). Test suite z **32 testami** (spec wymagał 30+) — wszystkie zielone. Pełny backend suite: **484 passed** (baseline 452 + 32). `check-all.sh`: 9/9 zielonych (visual regression skipped jako niepowiązany z backend story).
- Schema-level subtelność: `InviteTTLPreset` to `IntEnum` (int value); AC-1 wymaga string-name input. Rozwiązane przez `field_validator(mode="before")` mapujący `str` → `InviteTTLPreset[name]`. Behaviour: oba `{"ttl_preset": "ONE_DAY"}` i `{"ttl_preset": 86400}` są akceptowane (drugi wariant nieudokumentowany w spec, ale spójny z IntEnum semantic — Pydantic native).
- Endpoint dokumentacja OpenAPI: dodane `summary` + `description` do trzech endpointów (wymagane przez `test_openapi_agent_surface.py` gate dla tagu `admin`). Inne `admin`-tagged routery (`sot/admin_router.py`) trzymają ten sam pattern; `share/admin_router.py` jest excluded (legacy).

### File List

**NEW:**
- `apps/api/app/modules/invite/admin_router.py`
- `apps/api/app/modules/invite/admin_schemas.py`
- `apps/api/tests/test_invite_admin.py`

**MODIFIED:**
- `apps/api/app/modules/invite/__init__.py` (re-exports: +4 schemas, sorted `__all__`)
- `apps/api/app/router.py` (added `invite_admin_router` import + `include_router` registration)

## Change Log

- 2026-05-19 — Story 6.3 zaimplementowana: trzy admin endpointy invite (generate / list / revoke) + 32 testy + 4 Pydantic schemas + router wiring. Pełny backend suite 484/484 zielony, `check-all.sh` 9/9 zielonych (visual skipped).
