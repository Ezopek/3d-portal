# Story 6.5: Member permission expansion — `current_member_or_admin` dependency + share-router auth diff

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want a new `current_member_or_admin` dependency in `apps/api/app/core/auth/dependencies.py` plus a one-line dependency swap on `POST /api/admin/share` in `apps/api/app/modules/share/admin_router.py` (from `current_admin` → `current_member_or_admin`),
so that the brand-new member accounts produced by Story 6.4 `/register?token=` can actually mint share tokens for the catalog models they discover — closing FR5-MEMBER-1 ("a member-authenticated cookie POSTs `/api/share/` returning 201 with a fresh share token") and FR5-MEMBER-2 ("a member-authenticated cookie hitting any `/api/admin/*` route or any `/api/audit*` read returns 403") at the HTTP boundary with the SAME `current_admin` semantics preserved on every other admin route (per Decision C binding per-route allowlist table), no rename or relocation of the existing `share/admin_router.py` route (the swap is one line; the route remains under `/api/admin/share` for this story per minimum-scope rule — the architecture text "POST `/api/share/`" is a known doc-drift and is corrected separately, see Project Structure Notes § "Decision C URL-path drift"), and the existing `admin.share.create` / `admin.share.delete` audit-action vocabulary preserved verbatim (the action names are route-bound labels, NOT privilege-tier labels — a member-created share row still records `action="admin.share.create"` with `actor_user_id=<member_uuid>`; renaming the actions is out of scope, see Project Structure Notes § "Audit action vocabulary preserved").

## Acceptance Criteria

**AC-1 — `current_member_or_admin` dependency: admin AND member roles pass; agent and unknown roles get 403 `member_or_admin_required`; missing/invalid/expired tokens get the canonical 401 envelopes.**

- Given a fresh `apps/api/app/core/auth/dependencies.py` module loaded into a minimal `FastAPI()` test app with a single `GET /protected` route guarded by `current_member_or_admin` (mirrors the test-rig pattern from `apps/api/tests/test_auth_dependencies.py:14-32`),
- When the client (`fastapi.testclient.TestClient`) hits `/protected` with each of the eight cookie states below, then the response matches the table verbatim:

  | Cookie state | Role claim | HTTP | `detail` body | Notes |
  |---|---|---|---|---|
  | None set | — | 401 | `missing_access` | Mirrors `_decode()` `app/core/auth/dependencies.py:17`. |
  | Malformed JWT (`"not.a.jwt"`) | — | 401 | `invalid_access` | Mirrors `_decode()` line 24. |
  | Valid JWT with `exp` in the past (`ttl_minutes=-1`) | `admin` | 401 | `access_expired` | Mirrors `_decode()` line 22. |
  | Valid JWT, `role="admin"` | admin | 200 | n/a | Returns the JWT `sub` UUID. |
  | Valid JWT, `role="member"` | member | 200 | n/a | Returns the JWT `sub` UUID. |
  | Valid JWT, `role="agent"` | agent | 403 | `member_or_admin_required` | The `agent` role is INTENTIONALLY denied — share-link generation is for human members, not the service account. Binding per Decision C `current_admin` per-route allowlist (Init 0 `/api/admin/agent-runbook` is a separate nginx-bypass surface, not a member-or-admin share route). |
  | Valid JWT, `role="banana"` (unknown role) | — | 403 | `member_or_admin_required` | Defensive — unknown roles fail-closed. |
  | Valid JWT, `sub` not a UUID | admin | 401 | `invalid_access` | Mirrors `_resolve_admin()` line 33: malformed `sub` falls through to 401, NOT 403. |

- And the new dependency's HTTP-detail strings are snake_case (`member_or_admin_required`, `missing_access`, `invalid_access`, `access_expired`) — the repo convention from `_resolve_admin()` line 29 (`"admin_required"`) and `_resolve_user()` line 38 (`"forbidden_role"`). The architecture text "member or admin role required" (architecture.md §1466) is informal phrasing; the binding form is the snake_case code matching every other detail string in `dependencies.py` (NOT a sentence-with-spaces) — see Dev Notes § "Decision C dependency surface clarification". 
- And the new dependency is exported AT MODULE TOP-LEVEL alongside the existing `current_admin` + `current_user` as `current_member_or_admin = Depends(_current_member_or_admin_dep)` (matches the existing export shape from `dependencies.py:59-60` verbatim — single instance of `Depends(...)`, NOT `Annotated[uuid.UUID, Depends(...)]` syntax even though the architecture text uses the latter; the existing module's surface is the binding precedent).
- And the helper function `_resolve_member_or_admin(claims: dict) -> uuid.UUID` is a separate private function next to `_resolve_admin` and `_resolve_user` (matches the resolve/dep split convention from the existing module shape).

**AC-2 — `POST /api/admin/share` member happy-path: member cookie → 201 + share row + Redis key + `admin.share.create` audit row with `actor_user_id=<member_uuid>`.**

- Given the test fixture from `test_share_admin.py:14-67` (TestClient + `fakeredis.aioredis.FakeRedis()` swapped into `app.state.redis` + a seeded `Model` row + a member-role JWT cookie minted via `encode_token(subject=str(member_uuid), role="member", secret="test", ttl_minutes=30)` where `member_uuid = uuid.uuid4()` — the JWT-`sub` claim alone is enough; NO `user` row needs to exist in the DB because the share-router doesn't lookup the user via the DB, it only reads the JWT `sub`),
- When the client POSTs `/api/admin/share` with body `{"model_id": "<seeded-model-uuid>", "expires_in_hours": 24}` (the model must be a fresh seeded row from the fixture; NOT a deleted model — the route's `Model.deleted_at.is_(None)` filter at `admin_router.py:33` rejects soft-deleted models with 404, unchanged behavior),
- Then the response is HTTP 201 with body shape `{"token": "<urlsafe>", "url": "/share/<token>", "expires_at": "<ISO-8601 UTC>"}` (unchanged from Init 0 `CreateShareResponse` at `share/models.py:20-23`),
- And exactly one Redis key `share:token:<token>` exists with a TTL of ~86400 (24 hours; existing Init 0 `ShareService.create()` behavior — this AC verifies the dependency swap didn't break the service wiring, NOT that the service was re-implemented),
- And exactly one new row exists in `audit_log` with `action="admin.share.create"`, `entity_type="share_token"`, `entity_id=None` (preserved Init 0 contract — share-token audit rows key by token string in the `after` payload, not by a UUID PK — see `app/core/audit.py:24`), `actor_user_id=<member_uuid>` (the JWT `sub` decoded by the new dependency; this is the binding "audit pivot is the actor regardless of role" property), and an `after` JSON payload `{"token": "<token>", "model_id": "<model_uuid>"}` (unchanged from `admin_router.py:42-49`),
- And the audit action name STAYS as `admin.share.create` even though a member created the row — the action name is a route-bound label, NOT a privilege-tier label (see Project Structure Notes § "Audit action vocabulary preserved"). Verified by `assert audit.action == "admin.share.create"` after the member-driven POST.

**AC-3 — Admin path on `POST /api/admin/share` still works (no regression): admin cookie → 201 + admin-actor audit row.**

- Given the same fixture but with an ADMIN-role JWT cookie (the Init 0 default cookie shape from `test_share_admin.py:64`),
- When admin POSTs `/api/admin/share` with the same payload as AC-2,
- Then the response is HTTP 201, the share row exists, AND the audit row has `actor_user_id=<admin_uuid>` (NOT the member UUID from AC-2). This is the regression-prevention test for "swapping `current_admin` → `current_member_or_admin` MUST NOT drop admin-tier access" — admin is explicitly listed in the new dependency's allowed-role set.
- And every existing test in `apps/api/tests/test_share_admin.py` (4 tests: `test_create_share_requires_admin`, `test_create_share_returns_token_and_url`, `test_list_share_returns_active_tokens`, `test_revoke_share_removes_it`, `test_create_for_unknown_model_returns_404`) continues to pass unchanged. Note: `test_create_share_requires_admin` checks that an anonymous POST returns 401 — this still holds (the new dependency rejects missing cookies via the same `_decode()` 401 envelope). The test name is slightly misleading post-swap ("requires admin" is now "requires member-or-admin"), BUT the binding assertion `r.status_code == 401` still passes — see Dev Notes § "Test name preservation rationale".

**AC-4 — `GET /api/admin/share` and `DELETE /api/admin/share/{token}` stay admin-only: member cookie → 403 `admin_required`.**

- Given the test fixture with a member-role JWT cookie,
- When the client GETs `/api/admin/share` (list endpoint) OR DELETEs `/api/admin/share/<any-token>` (revoke endpoint),
- Then each response is HTTP 403 with body `{"detail": "admin_required"}` (matches the existing `_resolve_admin()` 403 envelope from `app/core/auth/dependencies.py:29`),
- And NO `audit_log` row is created for either request (the 403 fires INSIDE the dependency resolution, BEFORE the route function body executes, so no service call + no audit emission happens — same observable shape as Story 6.3 AC-4 `_clear_invite_and_audit_tables` assertion shape),
- And NO Redis key is created or modified,
- And `admin` cookies still pass through both endpoints unchanged (verified by re-running the existing `test_list_share_returns_active_tokens` + `test_revoke_share_removes_it` tests; both stay green).
- **Binding precedence:** ONLY `POST /api/admin/share` swaps to `current_member_or_admin`. The GET (list) + DELETE (revoke) routes stay on `current_admin` — see the per-route allowlist table in Decision C `architecture.md` §1474-1482.

**AC-5 — Member denial across the Init 0/Init 5 admin surface (FR5-MEMBER-2 coverage): member cookie → 403 on `/api/admin/audit`, `/api/admin/audit-log`, `/api/admin/invites`, `/api/admin/sentry-test`.**

- Given a member-role JWT cookie set on the TestClient,
- When the client hits each of the four currently-mounted admin surfaces:
  | Endpoint | Method | Source | Currently guarded by | Expected after Story 6.5 |
  |---|---|---|---|---|
  | `/api/admin/audit` | GET | `admin/router.py:55-81` | `current_admin` | 403 `admin_required` (no change) |
  | `/api/admin/audit-log` | GET | `admin/router.py:112-136` | `current_admin` | 403 `admin_required` (no change) |
  | `/api/admin/invites` | POST | `invite/admin_router.py:64-` (Story 6.3) | `current_admin` | 403 `admin_required` (no change) |
  | `/api/admin/invites` | GET | `invite/admin_router.py:120-` (Story 6.3) | `current_admin` | 403 `admin_required` (no change) |
  | `/api/admin/invites/{id}/revoke` | POST | `invite/admin_router.py:174-` (Story 6.3) | `current_admin` | 403 `admin_required` (no change) |
  | `/api/admin/sentry-test` | POST | `admin/router.py:40-42` | `current_admin` | 403 `admin_required` (no change) |
- Then EACH response is HTTP 403 with body `{"detail": "admin_required"}` (unchanged behavior — Story 6.5 swap is scoped to `POST /api/admin/share` only),
- And NO `audit_log` row is created for any of the six requests,
- This AC is the FR5-MEMBER-2 verifier ("member is denied all `/api/admin/*` + `/api/audit/*`; `current_admin` stays admin-only"). The verification is a regression check, NOT a new behavior — every one of these endpoints already returned 403 for member cookies before Story 6.5. The story adds these tests to make the binding contract explicit and to catch future drift if someone re-uses `current_member_or_admin` on the wrong route.
- **SoT admin routes (`/api/admin/categories`, `/api/admin/models`, `/api/admin/files`, etc.) are guarded by `_current_admin_or_agent_dep` (per `sot/admin_router.py:106-128`) — a DIFFERENT dependency from `current_admin`. A member cookie hitting any SoT admin route currently returns 403 `"Admin or agent role required"` (note: capital-A sentence-form detail, NOT snake_case — that's the existing SoT envelope shape; do NOT normalize in this story). This AC does NOT add SoT admin coverage to the test surface — those routes use a different dependency and are out of scope for Decision C (verified by architecture.md §1480-1481 per-route allowlist binding "All `/api/admin/*` — `current_admin` (no change)" where "All" specifically means the `current_admin`-guarded subset).**

**AC-6 — All endpoint flows test-covered with named tests; full backend suite green; ruff clean.**

- Given the test scaffolding established by Story 6.3 (`apps/api/tests/test_invite_admin.py` fixture shape with `_set_member_cookie()` helper at lines 85-92) and Story 6.4 (`apps/api/tests/test_invite_register.py`),
- When the dev agent ships Story 6.5,
- Then a NEW file `apps/api/tests/test_share_member_permission.py` is added containing AT LEAST the following test cases (binding names — Dev Agent TDD red-phase checklist):
  - `test_member_create_share_returns_201_with_token` — AC-2 happy path
  - `test_member_create_share_writes_audit_with_member_actor` — AC-2 audit assertions: action stays `admin.share.create`, `actor_user_id == member_uuid`
  - `test_member_create_share_writes_redis_key_consumable_by_public_route` — AC-2 Redis verification (indirect: confirm `GET /api/share/<token>` returns 200 — proves the key exists and is unexpired; avoids the fakeredis event-loop binding pitfall from Story 6.3 Sesja M)
  - `test_admin_create_share_still_returns_201` — AC-3 regression
  - `test_admin_create_share_audit_has_admin_actor` — AC-3 audit pivot verification
  - `test_member_list_share_returns_403_admin_required` — AC-4 (GET stays admin-only)
  - `test_member_delete_share_returns_403_admin_required` — AC-4 (DELETE stays admin-only)
  - `test_anonymous_create_share_returns_401_missing_access` — regression: anonymous still 401
  - `test_anonymous_list_share_returns_401_missing_access` — regression
  - `test_anonymous_delete_share_returns_401_missing_access` — regression
  - `test_agent_create_share_returns_403_member_or_admin_required` — AC-1 negative case at the HTTP layer (verifies the new dependency's `agent`-denial reaches the route)
  - `test_unknown_role_create_share_returns_403_member_or_admin_required` — AC-1 negative defensive case
  - `test_member_get_admin_audit_returns_403` — AC-5
  - `test_member_get_admin_audit_log_returns_403` — AC-5
  - `test_member_post_admin_invites_returns_403` — AC-5
  - `test_member_get_admin_invites_returns_403` — AC-5
  - `test_member_post_admin_invite_revoke_returns_403` — AC-5
  - `test_member_post_admin_sentry_test_returns_403` — AC-5
- And `apps/api/tests/test_auth_dependencies.py` is UPDATED (extended, NOT replaced) with the following NEW test cases (binding names — extend the existing fixture rig at `test_auth_dependencies.py:14-32` with a `@app.get("/member-or-admin-only")` route guarded by the new dependency):
  - `test_no_cookie_returns_missing_access_on_member_or_admin_route`
  - `test_expired_cookie_returns_access_expired_on_member_or_admin_route`
  - `test_invalid_cookie_returns_invalid_access_on_member_or_admin_route`
  - `test_valid_admin_cookie_passes_member_or_admin_route`
  - `test_valid_member_cookie_passes_member_or_admin_route`
  - `test_agent_role_blocked_from_member_or_admin_route` — assert 403 + `member_or_admin_required`
  - `test_unknown_role_blocked_from_member_or_admin_route` — assert 403 + `member_or_admin_required`
  - `test_non_uuid_sub_returns_invalid_access_on_member_or_admin_route` — AC-1 last row: `sub` not a UUID → 401, NOT 403 (matches `_resolve_admin()` line 33 + `_resolve_user()` line 42)
- And `pytest apps/api/tests/test_auth_dependencies.py -v` exits 0 with the existing 6 tests + 8 new tests = 14 tests green,
- And `pytest apps/api/tests/test_share_member_permission.py -v` exits 0 with all 18 tests green,
- And `pytest apps/api/ -q` exits 0 with NO regressions versus the Story 6.4 baseline (~508 tests; this story adds ~26 → expected ~534+),
- And `ruff format apps/api/` + `ruff check apps/api/` pass clean with NO `# noqa` exceptions (the repo's strict-clean policy),
- And `infra/scripts/check-all.sh` from the repo root exits 0 (all 10 stages green; matches the Story 6.4 close-out gate).

**AC-7 — Files, imports, registrations: full-file inventory + zero-drift wiring.**

- Given the existing conventions from `dependencies.py` + `share/admin_router.py` + `test_auth_dependencies.py` + `test_share_admin.py`,
- When the dev agent ships Story 6.5,
- Then the file inventory is EXACTLY:
  - **UPDATED** `apps/api/app/core/auth/dependencies.py` (add `_resolve_member_or_admin()`, `_current_member_or_admin_dep()`, and `current_member_or_admin = Depends(...)` export — see Dev Notes § "Implementation skeleton — dependencies.py" for the exact patch shape; ~25 added LOC total)
  - **UPDATED** `apps/api/app/modules/share/admin_router.py` (change line 8 import from `current_admin` to `current_admin, current_member_or_admin` AND line 30 `user_id: uuid.UUID = current_admin` to `user_id: uuid.UUID = current_member_or_admin` — TWO line edits, scoped to the `create_share()` function only; lines 59 + 69 stay on `current_admin`)
  - **UPDATED** `apps/api/tests/test_auth_dependencies.py` (extend with the 8 new test cases from AC-6 + the new `/member-or-admin-only` route definition in the `app_with_protected_routes` fixture)
  - **NEW** `apps/api/tests/test_share_member_permission.py` (~450 LOC: the 18 named tests from AC-6 + fixture wiring mirroring `test_share_admin.py` shape; seeds a `Model` row in the test DB per-test)
- And NO new top-level main.py edits are needed (the `current_member_or_admin` dependency lives in the existing `dependencies.py` module which is already imported by `share/admin_router.py`; no FastAPI middleware changes needed),
- And NO frontend changes are needed in this story:
  - The frontend `AuthContext` at `apps/web/src/shell/AuthContext.tsx:50-53` already exposes both `isAdmin` and `isMember` flags (the `isMember` flag was added in Story 6.4's prerequisite work — verified at line 52: `isMember: u.role === "member"`),
  - No share-creation UI affordance currently exists in the frontend (verified by `grep -rn "api/admin/share" apps/web/src` returning no matches) — Story 8.x admin-panel UI work will surface the member share button later. This story is BACKEND-ONLY.
  - The architecture text "share-router auth expansion" refers exclusively to the backend HTTP-layer dependency swap; no UI bindings ride along.
- And NO Alembic migration is needed (no schema changes — the existing `UserRole` enum already contains `member` per `app/core/db/models/_enums.py:10-13`, and no audit-action vocabulary changes ride along per AC-2 binding).
- And NO `KNOWN_ENTITY_TYPES` changes are needed (the entity types `share_token` + `user` are already registered per `app/core/audit.py:39, 42`; the audit actions emitted by this story are the existing `admin.share.create` / `admin.share.delete` — no new action names).
- And the new file passes `ruff format apps/api/` + `ruff check apps/api/` cleanly,
- And the OpenAPI surface DOES NOT change (no new routes; the swap is on the dependency only — OpenAPI doesn't surface dependency metadata in the path-spec). Verified by `pytest apps/api/tests/test_runbook_openapi_consistency.py -v` continuing to pass without modifications.

## Tasks / Subtasks

- [x] **T1 — Add `current_member_or_admin` dependency to `apps/api/app/core/auth/dependencies.py` (AC-1, AC-6, AC-7)**
  - [x] T1.1 RED — extend `apps/api/tests/test_auth_dependencies.py` with the 8 new tests from AC-6 + the new `/member-or-admin-only` route in the `app_with_protected_routes` fixture. The fixture's `app` MUST gain a second route alongside the existing `/admin-only` + `/user-only`: `@app.get("/member-or-admin-only")` with signature `def _moa(uid: uuid.UUID = current_member_or_admin): return {"uid": str(uid)}`. The fixture body needs ONE new import line: `from app.core.auth.dependencies import current_member_or_admin` (added to the existing import at `test_auth_dependencies.py:10`). Expected initial state: every new test fails with `ImportError` (the name does not yet exist).
  - [x] T1.2 GREEN — patch `apps/api/app/core/auth/dependencies.py` per Dev Notes § "Implementation skeleton — dependencies.py". Add:
    - `_resolve_member_or_admin(claims: dict[str, object]) -> uuid.UUID` — checks `claims.get("role") in ("admin", "member")` (binding tuple — the architecture lists "admin, member"; the order does not matter but the SET is the binding contract). On miss → `HTTPException(403, "member_or_admin_required")`. On non-UUID `sub` → `HTTPException(401, "invalid_access")` (matches `_resolve_admin()` line 33 fall-through).
    - `_current_member_or_admin_dep(portal_access, settings)` — the FastAPI dependency function with the same Cookie + Settings signature as `_current_admin_dep()` line 45-49.
    - `current_member_or_admin = Depends(_current_member_or_admin_dep)` — module-top-level export, single instance (matches the export shape on line 59-60).
  - [x] T1.3 Run `pytest apps/api/tests/test_auth_dependencies.py -v`. Expected: existing 6 tests still green + 8 new tests now green = 14 total.
  - [x] T1.4 Verify the new dependency exports cleanly: `python -c "from app.core.auth.dependencies import current_member_or_admin; print(type(current_member_or_admin).__name__)"` — expect `"Depends"` (the FastAPI dependency wrapper class).

- [x] **T2 — Swap `POST /api/admin/share` dependency from `current_admin` to `current_member_or_admin` (AC-2, AC-3, AC-4, AC-6, AC-7)**
  - [x] T2.1 RED — create `apps/api/tests/test_share_member_permission.py` with the fixture shape from `test_share_admin.py:14-67` (TestClient + fakeredis swap into `app.state.redis` + seeded `Model` row + JWT cookie minters for both admin AND member roles). The fixture should yield `(c: TestClient, admin_token: str, admin_uuid: uuid.UUID, member_token: str, member_uuid: uuid.UUID, model_ids: tuple[uuid.UUID, uuid.UUID])` so each test can pick whichever cookie it needs. Helper functions: `_set_admin_cookie(c, admin_token)` and `_set_member_cookie(c, member_token)` that wrap `c.cookies.set("portal_access", <token>)` (matches the `_set_admin_cookie()` / `_set_member_cookie()` helpers from `test_invite_admin.py:81-92`). Author the 18 named tests from AC-6 against the not-yet-swapped router. Expected initial state: the member happy-path test fails with HTTP 403 (current `current_admin` rejects member); other tests behave as before.
  - [x] T2.2 GREEN — edit `apps/api/app/modules/share/admin_router.py`:
    - **Line 8 import:** change `from app.core.auth.dependencies import current_admin` to `from app.core.auth.dependencies import current_admin, current_member_or_admin`. The names are sorted alphabetically (the project's ruff isort rules; matches the precedent of multi-name imports in `invite/admin_router.py:25` `from app.core.auth.dependencies import current_admin`).
    - **Line 30 parameter:** in the `create_share()` function signature, change `user_id: uuid.UUID = current_admin` to `user_id: uuid.UUID = current_member_or_admin`. ONE-LINE swap; the parameter name + type annotation stay identical so the function body (which already uses `user_id` for the audit `actor_user_id`) needs NO changes.
    - **Lines 59 (`_user_id: uuid.UUID = current_admin` in `list_share`) and 69 (`user_id: uuid.UUID = current_admin` in `revoke_share`) STAY ON `current_admin`** — per Decision C per-route allowlist, ONLY `POST /api/admin/share` is in the expansion set. Do NOT touch lines 59 or 69.
  - [x] T2.3 Run `pytest apps/api/tests/test_share_member_permission.py -v` — all 18 tests green.
  - [x] T2.4 Run `pytest apps/api/tests/test_share_admin.py -v` — existing 5 tests stay green (regression check). Of note: `test_create_share_requires_admin` is now misnamed (it tests "anonymous returns 401", not "non-admin returns 403"); the test assertion stays correct so the test stays green without modification. Per Dev Notes § "Test name preservation rationale", the test name is NOT changed in this story.
  - [x] T2.5 Verify the audit emission still works for both roles: in `test_member_create_share_writes_audit_with_member_actor`, explicitly assert `audit.action == "admin.share.create" and audit.actor_user_id == member_uuid`. In `test_admin_create_share_audit_has_admin_actor`, assert `audit.action == "admin.share.create" and audit.actor_user_id == admin_uuid`. The action name is INVARIANT across role; the actor pivot moves.

- [x] **T3 — Verify the FR5-MEMBER-2 denial surface across the existing admin routes (AC-5, AC-6)**
  - [x] T3.1 In `test_share_member_permission.py`, author the 6 named denial tests from AC-5 (`test_member_get_admin_audit_returns_403` etc.). Each test sets the member cookie, hits the named endpoint, and asserts `r.status_code == 403 and r.json()["detail"] == "admin_required"`. The conftest fixture's TestClient + `app.state.redis` swap already provides a working FastAPI app instance — the tests need NO additional service mocking because the 403 fires inside the dependency BEFORE the route body executes.
  - [x] T3.2 For the `POST /api/admin/invites` and `POST /api/admin/invites/{id}/revoke` tests, the request body shape needs to match the Story 6.3 schema (`{"role": "member", "ttl_preset": "ONE_DAY"}` for generate; empty body `{}` for revoke). The 403 fires before the schema validator runs, so even a syntactically-invalid body would still 403 — BUT keeping the body shape valid avoids any confusion about what the test is actually testing.
  - [x] T3.3 For `POST /api/admin/invite/{id}/revoke`, use any random UUID for `{id}` — the route never executes past the dependency, so the UUID does not need to correspond to a real invite row.
  - [x] T3.4 Run the 6 denial tests; all green.

- [x] **T4 — Final quality gate + status flip (all ACs)**
  - [x] T4.1 Run `pytest apps/api/tests/test_auth_dependencies.py -v` — 14 tests green.
  - [x] T4.2 Run `pytest apps/api/tests/test_share_member_permission.py -v` — 18 tests green.
  - [x] T4.3 Run `pytest apps/api/tests/test_share_admin.py -v` — 5 existing tests still green (regression).
  - [x] T4.4 Run `pytest apps/api/ -q` — full backend suite green; expected ~534+ tests (baseline 508 + 26 new).
  - [x] T4.5 Run `ruff format apps/api/` + `ruff check apps/api/` — clean. No `# noqa` exceptions.
  - [x] T4.6 Run `infra/scripts/check-all.sh` from repo root — all 10 stages green.
  - [x] T4.7 Update Dev Agent Record (Agent Model + Debug Log + Completion Notes + File List) below; flip `Status:` to `review`.

## Dev Notes

### Relevant architecture patterns and constraints

- **Decision C — member permission scope diff** (`architecture.md` §1458-1487): The binding decision text. Key bindings extracted:
  - **Dependency name:** `current_member_or_admin` (architecture line 1469). Distinct name from `current_admin` to encode the expanded scope explicitly — preserves the "permission expansion is one bit" property.
  - **Per-route allowlist** (architecture lines 1474-1484 — BINDING CONTRACT):
    - `POST /api/share/` (in code: `POST /api/admin/share`): `current_admin` → `current_member_or_admin` (THIS STORY)
    - `GET /api/share/{token}`: anonymous → anonymous (Init 0, no change)
    - `DELETE /api/share/{id}` (in code: `DELETE /api/admin/share/{token}`): `current_admin` → `current_admin` (no change)
    - `POST /api/share/{id}/revoke` (NOT in code — see drift note below): N/A
    - All `/api/admin/*`: `current_admin` → `current_admin` (no change; FR5-MEMBER-2)
    - `/api/audit/*` (read; in code: `/api/admin/audit`, `/api/admin/audit-log`): `current_admin` → `current_admin` (no change; FR5-MEMBER-2)
    - `/agent-runbook`: nginx-bypass → nginx-bypass (no change; Decision K)
    - `GET /api/catalog/*` + `GET /api/sot/*`: `current_user` → `current_user` (no change; catalog browse already gated to any authenticated user, including member by virtue of the `_ALLOWED_ROLES` set in `_resolve_user()` line 12)
  - **Alternatives rejected** (architecture line 1485):
    - "Add `member` to `current_admin` allowlist" — semantic drift; future readers cannot trust the dependency name.
    - "Generic role-based RBAC" — over-engineering for one route expansion.
    - "Reuse `current_user` on `POST /api/share/`" — drops role-gating entirely; agent role would slip through.

- **Init 0 dependency precedent** (`apps/api/app/core/auth/dependencies.py:1-61`): The existing module is the binding precedent for the new dependency's shape:
  - Two helper functions `_resolve_admin(claims) -> UUID` (lines 27-33) + `_resolve_user(claims) -> UUID` (lines 36-42) — pure functions that translate JWT claims into a UUID OR raise an HTTPException with a snake_case `detail` string.
  - Two dependency-glue functions `_current_admin_dep(portal_access, settings)` + `_current_user_dep(portal_access, settings)` (lines 45-56) — same Cookie + Settings injected-parameter signature.
  - Two module-top exports `current_admin = Depends(_current_admin_dep)` + `current_user = Depends(_current_user_dep)` (lines 59-60) — SINGLE instances of `Depends(...)`, NOT `Annotated[..., Depends(...)]`.
  - The story's new dependency MUST follow this triad: `_resolve_member_or_admin()` + `_current_member_or_admin_dep()` + `current_member_or_admin = Depends(...)`. The architecture text at line 1469 uses `Annotated[User, Depends(...)]` syntax — that is INFORMAL pseudocode; the binding form for this codebase is the module precedent.

- **JWT-only auth boundary** (no DB lookup on dependency): The existing `_resolve_admin` / `_resolve_user` take a `dict[str, object]` of decoded JWT claims and return a UUID — they NEVER query the DB to verify the user row exists. This is intentional: the JWT is the auth oracle, the DB is the audit oracle. The new dependency MUST follow the same pattern: take claims, check role, return UUID. Do NOT add a DB lookup for the User row. If a test wants a member with a real DB row (e.g., Story 6.4's register-flow tests), the test fixture can seed one; but the dependency itself reads only the JWT.

- **Audit emission conventions** (`apps/api/app/core/audit.py:47-84`): `record_event()` is the binding helper for all audit-row writes. Closed-set `entity_type` (line 28-44); `share_token` + `user` are already registered. The action-name vocabulary is documented inline at lines 14-27 — `share_token` audit rows currently use `admin.share.create` / `admin.share.delete` action names. **DO NOT add new action names in this story.** The route-bound names are preserved verbatim: when a member POSTs `/api/admin/share`, the audit row still records `action="admin.share.create"`. Rationale: the action name encodes the ROUTE, not the ACTOR's privilege tier (the `actor_user_id` column does that). Renaming the actions is a separate refactor (out of scope for Initiative 5 — there is no FR or audit-gate that requires it).

- **CSRF middleware coverage** (`app/core/auth/csrf.py:9-20`): The global `X-Portal-Client: web` CSRF guard applies to every `POST/PUT/PATCH/DELETE` on `/api/*` (except `/api/share/*`). `POST /api/admin/share` is covered — the conftest TestClient fixture sets the header by default (test_share_admin.py line 35 + test_invite_admin.py line 54). This story's tests inherit the same header-setting behaviour. No new middleware code; no CSRF-specific test scenarios needed for this story (CSRF coverage is already verified in `test_csrf_middleware.py` for the `/api/admin/*` path family).

- **FR5-MEMBER-1 + FR5-MEMBER-2 verification shapes** (`prd.md` § FR5 — confirmed via grep at `epics.md:1480-1481`):
  - FR5-MEMBER-1: "member role grants browse + viewer + `POST /api/share/`; share-router expands to `current_member_or_admin`" — verified by AC-2 happy path.
  - FR5-MEMBER-2: "member denied all `/api/admin/*` + `/api/audit/*`; `current_admin` stays admin-only" — verified by AC-4 + AC-5 denial surface.

### Implementation skeleton — `apps/api/app/core/auth/dependencies.py` (binding for shape)

Patch the existing file in-place. Final shape:

```python
"""apps/api/app/core/auth/dependencies.py"""

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import TokenError, decode_token
from app.core.config import Settings, get_settings

_ALLOWED_ROLES: frozenset[str] = frozenset({"admin", "agent", "member"})
_MEMBER_OR_ADMIN_ROLES: frozenset[str] = frozenset({"admin", "member"})


def _decode(token: str | None, settings: Settings) -> dict[str, object]:
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_access")
    try:
        return decode_token(token, secret=settings.jwt_secret)
    except TokenError as exc:
        msg = str(exc).lower()
        if "expired" in msg:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access_expired") from exc
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_access") from exc


def _resolve_admin(claims: dict[str, object]) -> uuid.UUID:
    if claims.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_required")
    try:
        return uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_access") from exc


def _resolve_user(claims: dict[str, object]) -> uuid.UUID:
    if claims.get("role") not in _ALLOWED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden_role")
    try:
        return uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_access") from exc


def _resolve_member_or_admin(claims: dict[str, object]) -> uuid.UUID:
    if claims.get("role") not in _MEMBER_OR_ADMIN_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "member_or_admin_required")
    try:
        return uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_access") from exc


def _current_admin_dep(
    portal_access: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> uuid.UUID:
    return _resolve_admin(_decode(portal_access, settings))


def _current_user_dep(
    portal_access: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> uuid.UUID:
    return _resolve_user(_decode(portal_access, settings))


def _current_member_or_admin_dep(
    portal_access: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> uuid.UUID:
    return _resolve_member_or_admin(_decode(portal_access, settings))


current_admin = Depends(_current_admin_dep)
current_user = Depends(_current_user_dep)
current_member_or_admin = Depends(_current_member_or_admin_dep)
```

### Implementation skeleton — `apps/api/app/modules/share/admin_router.py` patch (binding for shape)

Only two line edits. Before/after:

```diff
- from app.core.auth.dependencies import current_admin
+ from app.core.auth.dependencies import current_admin, current_member_or_admin
```

```diff
  @router.post("", status_code=201, response_model=CreateShareResponse)
  async def create_share(
      payload: CreateShareRequest,
      request: Request,
      session: Annotated[Session, Depends(get_session)],
-     user_id: uuid.UUID = current_admin,
+     user_id: uuid.UUID = current_member_or_admin,
  ) -> CreateShareResponse:
```

**DO NOT** touch the `list_share()` parameter at line 59 or the `revoke_share()` parameter at line 69. Per Decision C per-route allowlist, ONLY `POST /api/admin/share` (the `create_share` route) is in the expansion set.

### Implementation skeleton — `apps/api/tests/test_share_member_permission.py` (binding for shape)

```python
"""Tests for the Initiative 5 member permission expansion (Story 6.5).

Covers AC-2 through AC-6 from the Story 6.5 spec:
- POST /api/admin/share with member cookie → 201 (FR5-MEMBER-1)
- POST /api/admin/share with admin cookie → 201 (regression)
- GET / DELETE /api/admin/share with member cookie → 403 (per-route allowlist; FR5-MEMBER-2)
- GET /api/admin/audit, /api/admin/audit-log, /api/admin/invites, /api/admin/sentry-test
  with member cookie → 403 (FR5-MEMBER-2 verifier)
- Anonymous + agent + unknown-role cookies on POST /api/admin/share

Reuses the test_share_admin.py fixture shape verbatim (TestClient + fakeredis
swap + JWT cookie minting). Adds a member-role JWT alongside the admin one so
each test can pick the cookie state it needs.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import AuditLog, Category, Model, User
from app.core.db.session import get_engine
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings

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
        engine = get_engine()
        with Session(engine) as s:
            admin = s.exec(
                select(User).where(User.email == "admin@localhost.localdomain")
            ).first()
            admin_uuid = admin.id
            cat = Category(slug=f"share-cat-{uuid.uuid4().hex[:6]}", name_en="Cat")
            s.add(cat)
            s.flush()
            m1 = Model(
                slug=f"share-m1-{uuid.uuid4().hex[:6]}",
                name_en="M1",
                category_id=cat.id,
            )
            m2 = Model(
                slug=f"share-m2-{uuid.uuid4().hex[:6]}",
                name_en="M2",
                category_id=cat.id,
            )
            s.add(m1)
            s.add(m2)
            s.commit()
            model_ids = (m1.id, m2.id)
        admin_token = encode_token(
            subject=str(admin_uuid), role="admin", secret="test", ttl_minutes=30
        )
        member_uuid = uuid.uuid4()
        member_token = encode_token(
            subject=str(member_uuid), role="member", secret="test", ttl_minutes=30
        )
        yield c, admin_token, admin_uuid, member_token, member_uuid, model_ids, fake
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture(autouse=True)
def _clear_audit_table():
    """Wipe audit_log between tests for assertion isolation."""
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(AuditLog)).all():
            s.delete(row)
        s.commit()
    yield


def _set_cookie(c: TestClient, token: str) -> None:
    c.cookies.set("portal_access", token)


def _clear_cookie(c: TestClient) -> None:
    c.cookies.clear()


def _audit_rows(action: str) -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return list(s.exec(select(AuditLog).where(AuditLog.action == action)).all())


# ---------------------------------------------------------------------------
# AC-2: Member happy path on POST /api/admin/share
# ---------------------------------------------------------------------------

def test_member_create_share_returns_201_with_token(client):
    c, _, _, member_token, _, (mid, _), _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["url"].startswith("/share/")
    assert isinstance(body["token"], str) and len(body["token"]) > 0


def test_member_create_share_writes_audit_with_member_actor(client):
    c, _, _, member_token, member_uuid, (mid, _), _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201
    rows = _audit_rows("admin.share.create")
    assert len(rows) == 1
    assert rows[0].action == "admin.share.create"
    assert rows[0].actor_user_id == member_uuid
    after = json.loads(rows[0].after_json)
    assert after["model_id"] == str(mid)
    assert "token" in after  # share-token audit retains token in after_json (Init 0 contract; see app/core/audit.py:24)


def test_member_create_share_writes_redis_key_consumable_by_public_route(client):
    # Verify Redis key existence indirectly via the public consumption route.
    # Direct fakeredis assertions hit event-loop binding issues (cf. Story 6.3
    # Sesja M notes — fakeredis aioredis is bound to a different anyio loop
    # than the TestClient); using the in-process /api/share/{token} resolve
    # path is the proven pattern.
    c, _, _, member_token, _, (mid, _), _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201
    token = r.json()["token"]
    # Clear cookies — share-resolution is anonymous.
    _clear_cookie(c)
    r2 = c.get(f"/api/share/{token}")
    assert r2.status_code == 200, r2.text
    assert r2.json()["id"] == str(mid)


# ---------------------------------------------------------------------------
# AC-3: Admin path regression
# ---------------------------------------------------------------------------

def test_admin_create_share_still_returns_201(client):
    c, admin_token, _, _, _, (mid, _), _ = client
    _set_cookie(c, admin_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201


def test_admin_create_share_audit_has_admin_actor(client):
    c, admin_token, admin_uuid, _, _, (mid, _), _ = client
    _set_cookie(c, admin_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201
    rows = _audit_rows("admin.share.create")
    assert len(rows) == 1
    assert rows[0].actor_user_id == admin_uuid


# ---------------------------------------------------------------------------
# AC-4: GET + DELETE stay admin-only
# ---------------------------------------------------------------------------

def test_member_list_share_returns_403_admin_required(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.get("/api/admin/share")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_delete_share_returns_403_admin_required(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.delete("/api/admin/share/some-fake-token")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


# ---------------------------------------------------------------------------
# Anonymous regression
# ---------------------------------------------------------------------------

def test_anonymous_create_share_returns_401_missing_access(client):
    c, _, _, _, _, (mid, _), _ = client
    _clear_cookie(c)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


def test_anonymous_list_share_returns_401_missing_access(client):
    c, _, _, _, _, _, _ = client
    _clear_cookie(c)
    r = c.get("/api/admin/share")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


def test_anonymous_delete_share_returns_401_missing_access(client):
    c, _, _, _, _, _, _ = client
    _clear_cookie(c)
    r = c.delete("/api/admin/share/some-fake-token")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


# ---------------------------------------------------------------------------
# Agent + unknown-role denial on POST /api/admin/share (AC-1 negative paths)
# ---------------------------------------------------------------------------

def test_agent_create_share_returns_403_member_or_admin_required(client):
    c, _, _, _, _, (mid, _), _ = client
    agent_token = encode_token(
        subject=str(uuid.uuid4()), role="agent", secret="test", ttl_minutes=30
    )
    _set_cookie(c, agent_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 403
    assert r.json()["detail"] == "member_or_admin_required"


def test_unknown_role_create_share_returns_403_member_or_admin_required(client):
    c, _, _, _, _, (mid, _), _ = client
    bogus_token = encode_token(
        subject=str(uuid.uuid4()), role="banana", secret="test", ttl_minutes=30
    )
    _set_cookie(c, bogus_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 403
    assert r.json()["detail"] == "member_or_admin_required"


# ---------------------------------------------------------------------------
# AC-5: FR5-MEMBER-2 denial surface across admin routes
# ---------------------------------------------------------------------------

def test_member_get_admin_audit_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.get("/api/admin/audit")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_get_admin_audit_log_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.get("/api/admin/audit-log")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_post_admin_invites_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.post(
        "/api/admin/invites", json={"role": "member", "ttl_preset": "ONE_DAY"}
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_get_admin_invites_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.get("/api/admin/invites")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_post_admin_invite_revoke_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.post(f"/api/admin/invites/{uuid.uuid4()}/revoke")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_post_admin_sentry_test_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/sentry-test")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"
```

### Decision C dependency surface clarification

The architecture.md §1463-1470 pseudocode uses:

```python
async def _assert_member_or_admin(user: User = Depends(current_user)) -> User:
    if user.role not in (Role.member, Role.admin):
        raise HTTPException(status_code=403, detail="member or admin role required")
    return user

current_member_or_admin = Annotated[User, Depends(_assert_member_or_admin)]
```

This is INFORMAL pseudocode. The binding form for this codebase is the existing `_resolve_admin` / `_resolve_user` triad shape (see `apps/api/app/core/auth/dependencies.py:27-60`). Differences and rationale:

- **Return type:** architecture suggests `User` ORM row; codebase precedent is `uuid.UUID` (JWT `sub` claim). NO DB lookup happens in the dependency — the JWT is the auth oracle.
- **Detail string:** architecture suggests `"member or admin role required"` (sentence with spaces); codebase precedent is snake_case (`"admin_required"`, `"forbidden_role"`, `"missing_access"`, etc.). Binding: `"member_or_admin_required"`.
- **Export shape:** architecture suggests `Annotated[User, Depends(...)]`; codebase precedent is `Depends(...)` single-instance export (used as a parameter default). Binding: the single-instance form.

### Test name preservation rationale (`test_create_share_requires_admin`)

The existing test `apps/api/tests/test_share_admin.py:70-73` is named `test_create_share_requires_admin` but its assertion is just `r.status_code == 401` after an anonymous (no-cookie) POST. After Story 6.5, the route NO LONGER "requires admin" — it requires member-or-admin. The test name becomes slightly misleading.

The choice: keep the test name verbatim. Reasons:
1. **Assertion is still correct.** Anonymous POST returns 401 `missing_access` regardless of the dependency choice (the `_decode()` cookie-presence check at `dependencies.py:17` fires BEFORE the role check). The test still verifies what it claims to verify: "POST /api/admin/share without a cookie returns 401".
2. **Renaming is scope creep.** Changing the test name is a doc-only refactor; doing it in the same commit as the dependency swap would dilute the commit's reviewability.
3. **Coverage is preserved by the new file.** `test_share_member_permission.py` adds `test_anonymous_create_share_returns_401_missing_access` with the explicit name + explicit `missing_access` detail check — this is the authoritative anonymous-denial test post-Story 6.5.

If a future story chooses to rename the existing test, the new name should be `test_create_share_requires_authentication` to reflect the post-Story 6.5 reality. Not in scope here.

### Project Structure Notes

#### Decision C URL-path drift in architecture.md

The architecture document at §1474-1481 names the route as `POST /api/share/` for the dependency-swap target. The actual code mounts the route at `POST /api/admin/share` (`apps/api/app/modules/share/admin_router.py:18` prefix `/api/admin/share`). This is a doc drift in architecture.md (and in the duplicated reference in `epics.md:1608` + Decision G at §1589 + Decision H at §1635-1639).

**Resolution for Story 6.5:** Honor the code reality. The dependency swap is on the actual route at `/api/admin/share` (a one-line change). The architecture text "POST /api/share/" is interpreted as the intended logical resource ("the public-facing share-creation endpoint"); the physical URL stays at `/api/admin/share` until a separate doc-only correction pass updates the architecture.

**Follow-up:** Flag a doc-correction task in `_bmad-output/implementation-artifacts/triage-backlog.md` (or via `bmad-correct-course` post-ship) to fix the four architecture/epics references that say `/api/share/` when they mean `/api/admin/share`. Out of scope for Story 6.5 dev work; in scope for retro/correct-course.

#### Audit action vocabulary preserved

Architecture decisions do NOT call for renaming `admin.share.create` / `admin.share.delete` even though members now mint share rows. Rationale: the action name encodes the route, not the actor's privilege tier; the `actor_user_id` column carries the role pivot. AC-2 binding assertion `audit.action == "admin.share.create"` for member-driven create makes this explicit in the test surface.

Future story 8.x (admin invites UI) may revisit audit-action naming when bulk admin tooling lands; for now, the rename would touch >5 audit-row assertions across existing test files and offers no functional gain.

#### `admin_user_cookies` conftest fixture drift

Architecture cascade text at §1487 says: "Test fixture in `apps/api/tests/conftest.py` adds `member_user_cookies` analogous to existing `admin_user_cookies`."

**Drift:** `admin_user_cookies` does NOT exist in `apps/api/tests/conftest.py` (verified by `grep -n "admin_user_cookies\|member_user_cookies\|fixture.*cookies" apps/api/tests/conftest.py` returning zero matches). The test convention in this repo is per-file `client` fixtures that yield a TestClient + manually-minted JWT tokens (verified across `test_share_admin.py:14-67`, `test_invite_admin.py:34-65`, `test_invite_register.py`).

**Resolution for Story 6.5:** Follow the per-file convention. The new `test_share_member_permission.py` declares its own `client` fixture that yields `(c, admin_token, admin_uuid, member_token, member_uuid, model_ids, fake)`. NO conftest-level fixture additions ride along.

**Follow-up:** Promote per-file fixtures to conftest-level fixtures only when ≥3 test files need the same cookie-minting boilerplate. Stories 6.5 (this file), 6.6 (rate-limit member-IP cookies), 6.7 (per-member share cap), 7.x (2FA flows), 8.x (admin invites tab) will likely cross that threshold — flag for `bmad-correct-course` at Epic 7 mid-point.

#### `apps/api/tests/integration/` directory drift

Architecture cascade text at §1487 says: "Integration test `apps/api/tests/integration/test_share_member.py` covers happy-path + denial-path."

**Drift:** the `apps/api/tests/integration/` directory does NOT exist (verified by `find apps/api/tests -type d` returning only `tests/`, `tests/__pycache__/`, `tests/fixtures/`). All existing API tests live directly under `apps/api/tests/` (a flat layout, not pytest-split-by-marker).

**Resolution for Story 6.5:** Place the new file at `apps/api/tests/test_share_member_permission.py` (flat-directory convention; the `_permission` suffix disambiguates from the future `test_share_member.py` if any later story chooses to use that name). NO new `tests/integration/` directory; NO new pytest markers.

#### Per-route allowlist binding is one-direction

Decision C explicitly preserves `current_admin` on:
- `DELETE /api/admin/share/{token}` (revoke)
- `GET /api/admin/share` (list)
- All `/api/admin/audit*` reads
- All `/api/admin/invites*` (Story 6.3 admin endpoints)
- `/api/admin/sentry-test`

The risk to guard against: a future story authoring a new `current_admin`-guarded admin route could accidentally pull in `current_member_or_admin` from the import line. AC-5's six denial tests + AC-4's two-route denial tests together form the regression net. Add the FR5-MEMBER-2 verifier line to `_bmad-output/planning-artifacts/_runtime/test-coverage-map.md` (if such a map exists) — out of scope, just a note.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision C — Member permission scope diff] (lines 1458-1487; binding for dependency surface + per-route allowlist)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.5] (lines 1600-1611; acceptance check shape)
- [Source: _bmad-output/planning-artifacts/epics.md#FR5-MEMBER-1, FR5-MEMBER-2] (lines 1480-1481; FR table binding)
- [Source: apps/api/app/core/auth/dependencies.py] (lines 1-61; existing dependency triad — binding precedent for shape)
- [Source: apps/api/app/modules/share/admin_router.py] (lines 1-80; route file being patched — two-line edit)
- [Source: apps/api/tests/test_auth_dependencies.py] (lines 1-88; existing test rig — binding precedent for new test rows)
- [Source: apps/api/tests/test_share_admin.py] (lines 1-126; binding precedent for new file's fixture shape)
- [Source: apps/api/tests/test_invite_admin.py] (lines 81-92; `_set_admin_cookie` + `_set_member_cookie` helper pattern — binding precedent)
- [Source: apps/api/app/core/audit.py] (lines 14-44; KNOWN_ENTITY_TYPES + `admin.share.create/delete` action names — preserved)
- [Source: apps/api/app/core/auth/csrf.py] (lines 9-20; global CSRF middleware — already covers `POST /api/admin/share`)
- [Source: _bmad-output/implementation-artifacts/6-3-admin-invite-endpoints-generate-list-revoke.md] (Story 6.3 spec — fixture pattern for member-vs-admin cookie tests)
- [Source: _bmad-output/implementation-artifacts/6-4-public-register-endpoint-and-ui.md] (Story 6.4 spec — register flow that creates the member rows this story expands)
- [Source: apps/web/src/shell/AuthContext.tsx] (line 52: `isMember` flag already exposed — no frontend changes ride along)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — via Claude Code CLI, bmad-dev-story skill.

### Debug Log References

- Pragmatic deviation from spec § AC-2 "NO `user` row needs to exist in the DB" — the test fixture seeds a real `User(role=member)` row alongside the bootstrap admin. Rationale: `audit_log.actor_user_id` has a FK to `user.id` enforced by `PRAGMA foreign_keys = ON` (see `apps/api/app/core/db/session.py:18-21`); the happy-path audit emission would IntegrityError without a real row. The seeded row mirrors the actual Story 6.4 post-register state (every member account that can POST `/api/admin/share` in production necessarily has a `user` row). The dependency itself remains JWT-only — no DB lookup on the auth boundary; the FK constraint is purely a write-side concern at the audit-emission step downstream of the dependency.
- Ruff format pass after authoring touched 2 test files cosmetically (multiline arg → single-line `encode_token(subject="not-a-uuid", role="member", secret="test", ttl_minutes=10)`; admin-User `select(...).first()` collapsed onto one line). No semantic change; recorded for traceability.

### Completion Notes List

- T1: `current_member_or_admin` dependency added to `apps/api/app/core/auth/dependencies.py` with the binding triad shape (`_resolve_member_or_admin` helper + `_current_member_or_admin_dep` glue + module-top `current_member_or_admin = Depends(...)` export), mirroring the existing `_resolve_admin` / `_resolve_user` precedent verbatim. New `_MEMBER_OR_ADMIN_ROLES: frozenset[str] = frozenset({"admin", "member"})` constant alongside the existing `_ALLOWED_ROLES`. Snake_case `member_or_admin_required` 403 detail. Non-UUID `sub` falls through to 401 `invalid_access` (not 403) per the existing `_resolve_admin` precedent.
- T2: `apps/api/app/modules/share/admin_router.py` patched with the spec-binding two-line edit — import line gains `current_member_or_admin` (alphabetic sort preserved), `create_share()` signature swaps `user_id: uuid.UUID = current_admin` → `user_id: uuid.UUID = current_member_or_admin`. `list_share()` (line 59) and `revoke_share()` (line 69) untouched per Decision C per-route allowlist.
- T3: All 6 FR5-MEMBER-2 denial-surface tests authored in `test_share_member_permission.py` (member cookie hitting `/api/admin/audit`, `/api/admin/audit-log`, `POST /api/admin/invites`, `GET /api/admin/invites`, `POST /api/admin/invites/{id}/revoke`, `POST /api/admin/sentry-test` → 403 `admin_required`). All pass.
- T4 quality gate — full suite green:
  - `pytest apps/api/tests/test_auth_dependencies.py -v` → 14 passed (existing 6 + 8 new).
  - `pytest apps/api/tests/test_share_member_permission.py -v` → 18 passed.
  - `pytest apps/api/tests/test_share_admin.py -v` → 5 passed (regression intact).
  - `pytest apps/api -q` → 534 passed (508 baseline + 26 new = 534, matches spec target).
  - `ruff format apps/api/` → 2 files reformatted (cosmetic test-file changes only).
  - `ruff check apps/api/` → all checks passed.
  - `infra/scripts/check-all.sh` → all 10 stages green (apps/api ruff format+check, workers/render ruff format+check, apps/web typecheck+lint+vitest, apps/api pytest, workers/render pytest, apps/web visual regression 188 passed / 24 skipped).
- Audit-action vocabulary preserved verbatim per Project Structure Notes § "Audit action vocabulary preserved" — member-driven POST `/api/admin/share` still emits `action="admin.share.create"` with `actor_user_id=<member_uuid>`. Verified by `test_member_create_share_writes_audit_with_member_actor`.
- No frontend changes; `AuthContext.isMember` already exposed by Story 6.4. No Alembic migration. No `KNOWN_ENTITY_TYPES` additions. No CSRF middleware changes. No OpenAPI surface change (`pytest tests/test_runbook_openapi_consistency.py` continues to pass within the full-suite green).

### File List

- UPDATED `apps/api/app/core/auth/dependencies.py` — added `_MEMBER_OR_ADMIN_ROLES` constant, `_resolve_member_or_admin()` helper, `_current_member_or_admin_dep()` glue, `current_member_or_admin = Depends(...)` export (+18 LOC).
- UPDATED `apps/api/app/modules/share/admin_router.py` — import line + `create_share()` parameter swap (2-line diff).
- UPDATED `apps/api/tests/test_auth_dependencies.py` — `/member-or-admin-only` route in the test fixture + 8 new test functions covering AC-1 (existing 6 → 14 total).
- NEW `apps/api/tests/test_share_member_permission.py` — 18 tests covering AC-2 through AC-5 (member happy path; admin regression; GET/DELETE admin-only; anonymous 401; agent + unknown-role 403; FR5-MEMBER-2 denial across 6 admin endpoints).

### Change Log

- 2026-05-19 — Story 6.5 implementation complete (bmad-dev-story, Claude Opus 4.7). Added `current_member_or_admin` FastAPI dependency to `apps/api/app/core/auth/dependencies.py` (resolve/dep/export triad mirroring `_resolve_admin`; `member_or_admin_required` snake_case detail; JWT-only oracle). Swapped `POST /api/admin/share` from `current_admin` to `current_member_or_admin` (one-line dep change in `create_share()`); `GET /api/admin/share` (list) and `DELETE /api/admin/share/{token}` (revoke) stay on `current_admin` per Decision C per-route allowlist. Audit action `admin.share.create` preserved verbatim for member-created shares (route-bound, not privilege-tier label). Realizes FR5-MEMBER-1 (member-cookie POST → 201 + share token) and FR5-MEMBER-2 (member denied across `/api/admin/audit*`, `/api/admin/invites*`, `/api/admin/sentry-test`). 26 new tests, full backend suite 534/534, ruff clean, check-all.sh 10/10 green.
