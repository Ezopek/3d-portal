# Story 30.1: Authenticated share-resolve endpoint + return-URL plumbing

Status: ready-for-dev

## Story

As an **authenticated portal member visiting a `/share/<token>` URL from another member**,
I want **the frontend to resolve the share token to a `model_id` against an authenticated endpoint without breaking the existing anonymous share-view contract**,
so that **Story 30.2 (`MemberShareView`) can render the canonical catalog detail UI at the share URL, and Story 30.3's Sign in button can return me to the original share link after login**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25-init18.md` § §4.1 + §4.2 + §4.3 (Story 30.1 entry). Architectural anchor: Decision AA (`architecture.md` § Initiative 18). **Codex tag:** `gpt-5.5` (NFR-SECURITY adjacency per [[feedback_security_vector_enumeration]] + [[feedback_auth_boundary_contract_audit]]).

## Acceptance Criteria

### AC-1 — Endpoint exists at the correct prefix and uses standard auth dep

`GET /api/me/share-links/{token}/resolve` is mounted via `apps/api/app/modules/share/member_router.py` (existing module, `prefix="/api/me/share-links"`). The handler uses `current_user` dep (any authenticated role: admin / member / agent). NOT mounted under `/api/share/<token>/...` (Decision AA: separate prefix preserves NFR10 credentialless contract on the public family).

### AC-2 — Happy path 200 returns `{model_id, access}`

For a valid token + authenticated caller + non-soft-deleted model, returns HTTP 200 with body `{"model_id": "<uuid>", "access": "granted"}`. `ShareResolveResponse` Pydantic model lives in `apps/api/app/modules/share/models.py`. `access` field is `Literal["granted"]` (forward-compat for B7: future `Literal["granted", "request_needed"]` when granular sharing lands; out of scope today).

### AC-3 — 401 for anonymous caller

Anonymous request (no `portal_access` cookie, or expired/invalid JWT) returns 401 with detail per existing `current_user` dep contract (`"missing_access"` / `"access_expired"` / `"invalid_access"`). NO body fields leak token existence.

### AC-4 — Uniform 404 for invalid / expired / revoked token (NFR18-TOKEN-ENUMERATION-1)

Three failure modes return BYTE-IDENTICAL response body + status code:
- Token never existed (random 32-char string).
- Token existed but Redis TTL elapsed (test uses `await fakeredis.delete(...)` to simulate).
- Token existed but was revoked (test uses `ShareService.revoke(token)` to simulate).

Canonical response: `HTTP 404` + `{"detail": "Share token not found or expired"}` (mirrors `/api/share/{token}` resolve_share copy at `router.py:61` verbatim — avoids two different "not found" strings between public and member surfaces, which would itself be an enumeration oracle).

### AC-5 — Soft-deleted model returns 404 (uniform with token miss)

When the token resolves to a `model_id` whose `Model.deleted_at IS NOT NULL`, the endpoint returns the SAME 404 + same body as AC-4. No leakage that "the token is valid but the model is gone".

### AC-6 — NFR10 credentialless contract on public family preserved (pre-merge invariant)

Grep invariant: `grep -rnE "Depends\((get_)?current_(user|admin|member_or_admin|admin_or_agent)\)|= current_(user|admin|member_or_admin|admin_or_agent)" apps/api/app/modules/share/router.py` returns ZERO matches. The new endpoint MUST live in `member_router.py`, not in `router.py`.

### AC-7 — Route enforcement gate (`test_route_enforcement_gate.py`) passes without `_PUBLIC_ROUTES` mutation

The existing gate test at `apps/api/tests/test_route_enforcement_gate.py` MUST continue to pass after the new endpoint lands. The new path `/api/me/share-links/{token}/resolve` MUST NOT be added to `_PUBLIC_ROUTES` (it has `current_user` dep, so the gate accepts it). Pre-merge run: `uv run pytest apps/api/tests/test_route_enforcement_gate.py -v` returns green.

### AC-8 — `validateSearch` on `/login` route hardened against open-redirect via `next`

`apps/web/src/routes/login.tsx` line 197-202 currently accepts `next` as any non-empty string. AC-8 tightens this:
- `next` MUST start with `/` (single slash) — relative path on same origin.
- `next` MUST NOT start with `//` (protocol-relative URL — `//evil.com/path` → browser interprets as `https://evil.com/path`).
- `next` MUST NOT contain newlines / null bytes / control chars (defensive — JSON-parsed query strings can carry these).
- Invalid `next` is dropped silently (returns `LoginSearch` without `next` key — post-login defaults to `/`).

The frontend `SignInButton` (Story 30.3) navigates to `/login?next=/share/<token>` — all generated values are safe by construction; AC-8 hardens the surface against direct URL-bar manipulation.

### AC-9 — Vitest coverage for hardened `validateSearch` (2 cases)

- **RU-1 (positive):** `validateSearch({ next: "/share/abc123" })` returns `{ next: "/share/abc123" }`.
- **RU-2 (negative):** `validateSearch({ next: "//evil.com/path" })` returns `{}` (next dropped). Same for `"https://evil.com"`, `"javascript:alert(1)"`, `"\n/path"`, `""` (already covered by `length > 0`).

### AC-10 — No new audit emission on resolve (read-only contract)

The new endpoint MUST NOT call `record_event(...)`. Mirrors the existing `list_my_share_links` (line 47-53 of `member_router.py`) and `get_share_asset` read-pattern conventions. If operator later wants "who-resolved-what" telemetry, it's a follow-up TB (out of scope).

### AC-11 — `ShareResolveResponse` does NOT leak token-state fields in 200 body

Pre-merge invariant: `ShareResolveResponse` model in `models.py` has EXACTLY two fields: `model_id` (UUID) and `access` (Literal). NO `expires_at`, `revoked_at`, `created_at`, `created_by`, or `token` fields. Token-state inspection requires the member-list endpoint (`GET /api/me/share-links`, Story 16.3) which already filters to `created_by == current_user`; the resolve endpoint is for foreign-issued tokens and MUST NOT expose creator/expiry to an arbitrary authenticated caller.

### AC-12 — Service-layer reuse: NO new `ShareService` method

Pre-enumeration discovery (2026-05-25): `ShareService.resolve(token: str) -> ShareToken | None` already exists at `apps/api/app/modules/share/service.py:40-44`. The new endpoint MUST REUSE this existing method. Spec author MUST NOT add a parallel `ShareService.resolve_for_member()` or similar duplicate. (TB-024-class pre-enumeration save: original SCP §4.4 mentioned "add `ShareService.resolve()` method" — this turned out to be already-shipped via Init 10 Story 16.3.)

## Tasks / Subtasks

- [ ] **T1** (AC-2, AC-11) — Add `ShareResolveResponse` Pydantic model to `apps/api/app/modules/share/models.py`
  - [ ] T1.1 Append class after `ShareModelView` (line 51 area) with two fields: `model_id: uuid.UUID` and `access: Literal["granted"]`. Include `Literal` import from `typing`.
  - [ ] T1.2 Docstring: "Initiative 18 Story 30.1 (Decision AA) — minimal projection for authenticated share-resolve. NO token-state fields per AC-11 enumeration-protection."

- [ ] **T2** (AC-1, AC-2, AC-3, AC-4, AC-5, AC-10, AC-12) — Add `resolve_my_share_link` handler to `apps/api/app/modules/share/member_router.py`
  - [ ] T2.1 Add new `@router.get("/{token}/resolve", response_model=ShareResolveResponse, summary=..., description=...)` decorator. Import `ShareResolveResponse` from `app.modules.share.models`. Import `Session` + `select` + `Model` + `get_session` to perform the soft-delete filter.
  - [ ] T2.2 Handler signature: `async def resolve_my_share_link(token: str, request: Request, session: Annotated[Session, Depends(get_session)], user_id: uuid.UUID = current_user) -> ShareResolveResponse`. The `user_id` is unused inside the body BUT MUST stay in the signature so the dep tree carries `current_user` (AC-1 + AC-7). Rename to `_user_id` if linter complains (mirrors `admin_router.py:59` precedent: `_user_id: uuid.UUID = current_admin`).
  - [ ] T2.3 Body Step 1 — call `record = await _service(request).resolve(token)`. If `None`, raise `HTTPException(404, "Share token not found or expired")` (AC-4 uniform 404).
  - [ ] T2.4 Body Step 2 — soft-delete check: `model = session.exec(select(Model).where(Model.id == record.model_id, Model.deleted_at.is_(None))).first()`. If `None`, raise the SAME `HTTPException(404, "Share token not found or expired")` (AC-5). Do NOT use a different detail string.
  - [ ] T2.5 Body Step 3 — return `ShareResolveResponse(model_id=record.model_id, access="granted")`. NO `record_event(...)` call (AC-10).
  - [ ] T2.6 Endpoint description (FastAPI `description=` kwarg): explicitly note "Init 18 Story 30.1 — paired with Story 30.2 `MemberShareView`. Uniform 404 on invalid/expired/revoked/soft-deleted (NFR18-TOKEN-ENUMERATION-1). Does NOT touch `/api/share/<token>/*` public family (Decision AA prefix separation)."

- [ ] **T3** (AC-8, AC-9) — Harden `validateSearch` in `apps/web/src/routes/login.tsx`
  - [ ] T3.1 Replace lines 197-202 `validateSearch` body. New shape:
    ```typescript
    validateSearch: (raw: Record<string, unknown>): LoginSearch => {
      const out: LoginSearch = {};
      if (typeof raw.next === "string" && _isSafeReturnPath(raw.next)) {
        out.next = raw.next;
      }
      if (raw.reset === "success") out.reset = "success";
      return out;
    },
    ```
  - [ ] T3.2 Add module-level helper `_isSafeReturnPath` near the top of `login.tsx` (above the `Login` component):
    ```typescript
    // Initiative 18 Story 30.1 AC-8 — defend against open-redirect via ?next.
    // Accept ONLY same-origin relative paths starting with a single "/" and
    // free of control chars. Reject "//evil.com" (protocol-relative), absolute
    // URLs, "javascript:" scheme, embedded newlines/null/control bytes.
    function _isSafeReturnPath(value: string): boolean {
      if (value.length === 0) return false;
      if (!value.startsWith("/")) return false;
      if (value.startsWith("//")) return false;
      // eslint-disable-next-line no-control-regex
      if (/[\x00-\x1f\x7f]/.test(value)) return false;
      return true;
    }
    ```
  - [ ] T3.3 Verify the 3 existing `await navigate({ to: next as "/" })` call sites (lines 62-63, 67-68, 85-86) DO NOT need changes — they already use `search.next || "/"` so if `next` was dropped by hardened `validateSearch`, the fallback to `/` kicks in.

- [ ] **T4** (AC-9) — Add vitest tests for `_isSafeReturnPath` + `validateSearch`
  - [ ] T4.1 Extend `apps/web/src/routes/login.test.tsx` with a new `describe("validateSearch open-redirect hardening (Story 30.1 AC-8)", () => {...})` block.
  - [ ] T4.2 Test RU-1 (positive cases): assert `Route.options.validateSearch({ next: "/share/abc123" })` returns `{ next: "/share/abc123" }`; same for `"/catalog/xyz"`, `"/settings/2fa"`. (Use `Route.options.validateSearch` per TanStack Router test pattern — `Route` is the exported `createFileRoute` result.)
  - [ ] T4.3 Test RU-2 (negative cases): assert `Route.options.validateSearch({ next: <bad> })` returns `{}` for each: `"//evil.com/path"`, `"https://evil.com"`, `"http://evil.com"`, `"javascript:alert(1)"`, `"\n/path"`, `""`, `"relative-no-slash"`.

- [ ] **T5** (AC-1, AC-2, AC-3, AC-4, AC-5, AC-10, AC-11) — Pytest coverage in `apps/api/tests/test_share_member_router.py`
  - [ ] T5.1 Reuse existing `client` + `seed_two_users_and_model` fixtures (lines 21-73 of the existing test file). No new fixtures needed.
  - [ ] T5.2 **RESOLVE-1 happy path** `test_resolve_my_share_link_happy_path_returns_200_with_model_id`:
    - Seed model + create share token via `POST /api/admin/share` as user_a (admin).
    - Switch cookies to user_b (member); `GET /api/me/share-links/{token}/resolve`.
    - Assert 200; body keys exactly `{"model_id", "access"}`; `model_id` == seeded `model_id`; `access` == `"granted"`. Assert NO `expires_at` / `revoked_at` / `token` / `created_by` keys (AC-11 enumeration-protection).
  - [ ] T5.3 **RESOLVE-2 anonymous** `test_resolve_my_share_link_requires_authentication`:
    - Create token as user_a; clear cookies; `GET /api/me/share-links/{token}/resolve`.
    - Assert 401; detail in {`"missing_access"`, `"access_expired"`, `"invalid_access"`} per `current_user` dep contract.
  - [ ] T5.4 **RESOLVE-3 invalid token** `test_resolve_my_share_link_invalid_token_returns_uniform_404`:
    - Authenticate as user_a; `GET /api/me/share-links/{uuid.uuid4().hex}/resolve` (random 32-char string).
    - Assert 404; body `{"detail": "Share token not found or expired"}` (byte-identical to other failure modes).
  - [ ] T5.5 **RESOLVE-4 expired token** `test_resolve_my_share_link_expired_token_uniform_404`:
    - Create token as user_a (1-hour expiry). Switch to user_b. Reach into fakeredis (via `isolated_client[1]`) and `await fakeredis.delete("share:token:" + token)` to simulate Redis TTL expiry.
    - `GET /api/me/share-links/{token}/resolve`.
    - Assert 404; body BYTE-IDENTICAL to RESOLVE-3 (use `assert r.text == invalid_text` comparing string outputs).
  - [ ] T5.6 **RESOLVE-5 revoked token** `test_resolve_my_share_link_revoked_token_uniform_404`:
    - Create token as user_a; user_a revokes via `DELETE /api/me/share-links/{token}`.
    - Switch to user_b; `GET /api/me/share-links/{token}/resolve`.
    - Assert 404; body BYTE-IDENTICAL to RESOLVE-3 + RESOLVE-4.
  - [ ] T5.7 **RESOLVE-6 soft-deleted model** `test_resolve_my_share_link_soft_deleted_model_uniform_404`:
    - Create token as user_a; soft-delete the model via direct SQLModel session: `model.deleted_at = datetime.now(UTC); session.commit()`.
    - Switch to user_b; `GET /api/me/share-links/{token}/resolve`.
    - Assert 404; body BYTE-IDENTICAL to RESOLVE-3.
  - [ ] T5.8 **CONTRACT-1 NFR10 grep** `test_share_public_router_carries_no_auth_depends_after_init_18`:
    - Locate `apps/api/app/modules/share/router.py` file content (via `inspect.getsource(app.modules.share.router)`).
    - Assert no occurrences of substrings: `"current_user"`, `"current_admin"`, `"current_member_or_admin"`, `"current_admin_or_agent"`. (Substring scan — module-level grep AC, NOT walking the AST.)

- [ ] **T6** (AC-7) — Verify route enforcement gate stays green
  - [ ] T6.1 Run `uv run pytest apps/api/tests/test_route_enforcement_gate.py -v` and confirm both tests pass.
  - [ ] T6.2 Manually inspect the gate test output for the new path `/api/me/share-links/{token}/resolve` — it should NOT appear in `violations` (because it carries `current_user` dep).

- [ ] **T7** (full quality gate) — Pre-merge invariants
  - [ ] T7.1 `cd /home/ezop/repos/3d-portal && timeout 600 uv run --project apps/api pytest apps/api/tests/ -v` returns green; new test count = baseline + 7 (T5.2–T5.8).
  - [ ] T7.2 `cd /home/ezop/repos/3d-portal/apps/api && uv run ruff format` (auto-fix) + `uv run ruff check` (assert clean).
  - [ ] T7.3 `cd /home/ezop/repos/3d-portal/apps/web && npm run test -- --run` returns green; new vitest count = baseline + 2 (RU-1, RU-2).
  - [ ] T7.4 `cd /home/ezop/repos/3d-portal/apps/web && npm run lint && npx tsc --noEmit` returns clean.
  - [ ] T7.5 **Pre-merge grep checklist (5 invariants):**
    - [ ] G1: `grep -rnE "Depends\(.*current_" apps/api/app/modules/share/router.py` returns ZERO (AC-6).
    - [ ] G2: `grep -nE "/{token}/resolve|/{token}/resolve" apps/api/app/modules/share/member_router.py` returns ONE hit (the new route decorator).
    - [ ] G3: `grep -nE "expires_at|revoked_at|created_by|created_at" apps/api/app/modules/share/models.py` returns NO hits inside `class ShareResolveResponse` body (use `awk` or inspect manually to scope; T5 RESOLVE-1 also asserts at HTTP level).
    - [ ] G4: `grep -nE "_isSafeReturnPath" apps/web/src/routes/login.tsx` returns 2+ hits (helper definition + 1+ caller in `validateSearch`).
    - [ ] G5: `grep -nE "record_event" apps/api/app/modules/share/member_router.py` returns EXACTLY 1 hit (the existing `revoke_my_share_link` line 79 — the new resolve handler does NOT add a 2nd hit per AC-10).

- [ ] **T8** (handoff to deploy + Story 30.2) — Document close-out
  - [ ] T8.1 Story file Dev Agent Record gets file list + completion notes per template.
  - [ ] T8.2 Sprint-status flip `30-1-share-resolve-endpoint-return-url: ready-for-dev → in-progress → review → done` per BMAD convention (dev-story owns the `→ review` flip; codex-review-pass owns the `→ done` flip).
  - [ ] T8.3 Note in close-out commit message: `next:` field on `LoginSearch` is now hardened — Story 30.2 + 30.3 can safely pass `/share/<token>` paths without additional validation on the producer side.

## Dev Notes

### Source-of-truth references

- **PRD:** `_bmad-output/planning-artifacts/prd.md` § Initiative 18 — FR18-SHARE-RESOLVE-1, FR18-SHARE-RESOLVE-2, FR18-RETURN-URL-1 (FE-plumbing portion), NFR18-SHARE-ANON-CONTRACT-1, NFR18-TOKEN-ENUMERATION-1.
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md` § Initiative 18 Decision AA — "Authenticated share-resolve endpoint placement" (prefix rationale + token-status-enumeration protection).
- **SCP:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25-init18.md` § §4.1 + §4.2 + §4.3 (Story 30.1 entry, including pre-merge invariants checklist).
- **Brainstorm:** `_bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md` (α-5 return-URL edge case, x-class threat vectors).
- **UX:** `_bmad-output/ux/share-flow-membership-path-ux.md` § "Implementation hooks for `bmad-correct-course`" — backend authenticated branch placement guidance.
- **Memory entries (mandatory):**
  - [[feedback_auth_boundary_contract_audit]] — auth-boundary commits/SCPs that reference existing code state REQUIRE explicit enumeration phase first (DONE in this spec — see "Pre-enumeration findings" below).
  - [[feedback_security_vector_enumeration]] — SCPs with NFR-SECURITY-* tag MUST list cookie-sending vectors + auth-state-consultation points + browser-default-credentials behaviors in § Threat vectors enumerated (see § "Threat vectors enumerated" below).
  - [[feedback_codex_model_routing]] — Story 30.1 routed to `gpt-5.5` per NFR-SECURITY adjacency (see top of file).
  - [[feedback_pre_merge_gate_checklist]] — T7 pre-merge invariants list is the operational gate.
  - [[feedback_share_view_scope_boundary]] (amended 2026-05-25) — carve-out language explicitly permits this endpoint as "membership-path completion, NOT share-view enrichment".

### Pre-enumeration findings (saved scope cuts)

Per [[feedback_scp_pre_enumeration_phase]] enumeration phase 2026-05-25:

1. **`ShareService.resolve(token: str) -> ShareToken | None` ALREADY EXISTS** at `apps/api/app/modules/share/service.py:40-44`. Originally added with Init 0; currently consumed by 5 call sites (`router.py:58`, `router.py:272`, `router.py:420`, `member_router.py:73` revoke flow, `admin_router.py:22` indirectly via `_service`). **Scope cut:** Story 30.1 does NOT add a new service method. T1 (Pydantic model) + T2 (handler) only — the service layer stays untouched.
2. **`current_user` dep + `member_router.py` mount pattern** are already established by Init 10 Story 16.3. **Scope cut:** no new dep needed; no new router file needed; no `app/router.py` include_router addition needed (member_router already mounted at line 26).
3. **`isolated_client` fixture + `seed_two_users_and_model` fixture** already cover the cookie-swap pattern for cross-user tests. **Scope cut:** no new test fixtures needed; T5 reuses existing infrastructure.
4. **`test_route_enforcement_gate.py`** mechanically asserts NFR10 across the whole route table. **Scope cut:** the new endpoint automatically passes the gate (carries `current_user` per AC-1); no allowlist mutation, no Sprint Change Proposal-gated `_PUBLIC_ROUTES` entry.

Net scope after enumeration: **2 files modified (models.py, member_router.py, login.tsx) + 1 test file extended + 0 service methods added + 0 fixtures added + 0 migration + 0 dependency added**. Very small footprint.

### Threat vectors enumerated (per [[feedback_security_vector_enumeration]])

The Story 30.1 surface adds:
- (a) A new authenticated endpoint adjacent to the public bypass family.
- (b) A frontend `next` query-param convention extended to `/share/<token>` paths.

Threat-vector enumeration (Codex-counterfactual self-grill):

| # | Vector | Story 30.1 mitigation | Test coverage |
|---|--------|----------------------|---------------|
| TV-1 | **Token-enumeration probe via resolve endpoint** — attacker iterates `GET /api/me/share-links/<random>/resolve` to enumerate valid tokens. | Authenticated (401 without cookie); uniform 404 for invalid/expired/revoked/soft-deleted (AC-4 + AC-5). Per-auth-scope rate-limit (existing `current_user` dep doesn't add a per-route limit, but global limits apply). | RESOLVE-3 / -4 / -5 / -6 + RESOLVE-2 |
| TV-2 | **CSRF on resolve endpoint** — read-only GET; browser-issued requests carry cookies regardless of CORS. | Inapplicable: GET is in `csrf.py:6 SAFE_METHODS` (CSRF middleware only checks POST/PUT/PATCH/DELETE). No state change ⇒ CSRF inapplicable per CSRF threat model (CSRF concerns ARE relevant for state-changing operations). Documented here for completeness. | N/A (negative-by-design) |
| TV-3 | **Cross-tenant access** — authenticated user_b resolves a share token created by user_a. | Per Decision AA + AC-2 happy path: this is INTENDED behavior (the use case IS member-receives-share-from-another-member). The endpoint deliberately does NOT filter by `created_by == user_id` (unlike `list_my_share_links` line 52). Documented assumption: all members have access to all models today (member-to-member visibility model). When future B7 granular sharing lands, the response `access` field flips from `"granted"` to `"request_needed"` for users without model access. | RESOLVE-1 (user_b resolves user_a's token) |
| TV-4 | **Token leakage in response body** — 200 response includes `expires_at` / `created_by` / `token` → enables enumeration probe to extract token-state without 404 oracle. | AC-11 + T1.1: `ShareResolveResponse` has EXACTLY 2 fields (`model_id`, `access`). Pre-merge grep G3 + RESOLVE-1 assertion on response body keys. | RESOLVE-1 keys-assert + T7.5 G3 |
| TV-5 | **Open-redirect via `next` query param** — attacker crafts `/login?next=//evil.com/phishing`; user logs in; SPA navigates to evil.com. | AC-8 + T3 hardening: `_isSafeReturnPath` enforces `next` MUST start with single `/`, NOT `//`, no control chars. Invalid `next` silently dropped. TanStack Router's typed `to:` cast `next as "/"` is an internal-routing call that historically rejects absolute URLs at runtime, but defense-in-depth via `validateSearch` is the explicit gate. | RU-2 (vitest) |
| TV-6 | **`javascript:` / `data:` URI scheme in `next`** — `next=javascript:alert(1)` → if navigated, executes XSS. | AC-8 + T3: any value not starting with `/` (single slash) is rejected. `javascript:` doesn't start with `/`. | RU-2 (vitest) |
| TV-7 | **Newline / null byte injection in `next`** — header smuggling, log poisoning, downstream parser confusion. | AC-8 + T3: `/[\x00-\x1f\x7f]/.test(value)` rejects control chars. | RU-2 (vitest) |
| TV-8 | **Logged-in user resolves token → screenshot URL bar → share screenshot publicly** — recipient's URL bar shows `/share/<token>`. | Out of scope for Story 30.1 — same property as today's anonymous share. Mitigated at sender's discretion (don't share screenshots of share URLs). No new attack surface introduced. | N/A |
| TV-9 | **Browser back-button after login lands on `/login?next=/share/<token>`** — user logs in, navigates away, hits back → /login form again. | Pre-existing TanStack behavior; not introduced by Story 30.1. Story 30.2's `MemberShareView` will handle the post-login `/share/<token>` arrival path correctly per AppShell Decision AB conditional bypass. | N/A |
| TV-10 | **Race: token revoked between `GET /share/<token>` initial page-load and `GET /api/me/share-links/<token>/resolve` follow-up** — share view shows model briefly, then fails. | Handled gracefully: `MemberShareView` (Story 30.2) catches 404 on resolve and falls back to anonymous-share-view-style "token invalid or expired" copy. Not a Story 30.1 concern (pure backend; FE handling lives in 30.2). | N/A (Story 30.2 owns) |

No P1/P2 unmitigated vector identified.

### Files this story touches (READ existing state before editing)

| File | Action | Why |
|---|---|---|
| `apps/api/app/modules/share/models.py` | EXTEND (add `ShareResolveResponse` class) | T1 — Pydantic model for endpoint response |
| `apps/api/app/modules/share/member_router.py` | EXTEND (add `resolve_my_share_link` handler) | T2 — endpoint implementation |
| `apps/web/src/routes/login.tsx` | MODIFY (replace `validateSearch` body + add `_isSafeReturnPath` helper) | T3 — open-redirect hardening |
| `apps/web/src/routes/login.test.tsx` | EXTEND (new describe block, 2 tests) | T4 — vitest coverage for AC-8/AC-9 |
| `apps/api/tests/test_share_member_router.py` | EXTEND (7 new tests T5.2–T5.8) | T5 — pytest coverage for AC-1..AC-11 |

**Files this story MUST NOT touch:**

- `apps/api/app/modules/share/router.py` — NFR10 credentialless contract (AC-6 grep invariant + AC-7 route gate).
- `apps/api/app/modules/share/service.py` — service method already exists (pre-enumeration AC-12).
- `apps/api/app/main.py:_PUBLIC_ROUTES` — new endpoint has `current_user` dep; allowlist mutation would be a SCP-gated change per FR6-AUTH-2 (not appropriate for this story).
- `apps/api/app/router.py` — `share_member_router` already included at line 26.
- `apps/api/app/modules/share/admin_router.py` — admin-only writes; orthogonal to Story 30.1.
- `apps/web/src/shell/AppShell.tsx` — Story 30.2 owns the AppShell bypass conditional (Decision AB).
- `apps/web/src/lib/api.ts` — existing `api()` wrapper already handles cookies + CSRF + 401-retry; Story 30.2's `MemberShareView` will consume it as-is.

### Implementation skeleton

**`apps/api/app/modules/share/models.py`** (append after `ShareModelView`, line ~52):

```python
from typing import Literal

# ... existing imports + classes ...


class ShareResolveResponse(BaseModel):
    """Initiative 18 Story 30.1 (Decision AA) — minimal projection for the
    authenticated share-resolve endpoint at GET /api/me/share-links/{token}/resolve.

    Exactly two fields. NO token-state fields (expires_at / revoked_at /
    created_by / token) per AC-11 enumeration-protection contract: the
    response is consumed by any authenticated user, not just the token's
    creator, so leaking creation/expiry metadata would enable a brute-force
    enumeration probe to infer token state from non-404 responses.

    The ``access`` field is forward-compat for B7 (future granular sharing):
    today it is always ``"granted"``; when granular sharing lands, B7 callers
    without model access will receive ``access="request_needed"`` plus a
    distinct response body shape that surfaces a request-access affordance.
    """

    model_id: uuid.UUID
    access: Literal["granted"]
```

**`apps/api/app/modules/share/member_router.py`** (append after `revoke_my_share_link`, line ~88):

```python
# ... existing imports ...
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, select

from app.core.db.models import Model
from app.core.db.session import get_session
from app.modules.share.models import ShareResolveResponse, ShareToken
# (ShareToken import may already be present)


@router.get(
    "/{token}/resolve",
    response_model=ShareResolveResponse,
    summary="Resolve a share token to its model_id for the authenticated caller",
    description=(
        "Initiative 18 Story 30.1 (Decision AA) — paired with Story 30.2 "
        "`MemberShareView` to enable B5 (active member receiving a share "
        "link from another member) enrich-in-place rendering at "
        "/share/<token>. Returns 200 with {model_id, access:'granted'} for "
        "a valid token + non-soft-deleted model. Uniform 404 on invalid / "
        "expired / revoked / soft-deleted (NFR18-TOKEN-ENUMERATION-1). "
        "Does NOT touch the /api/share/<token>/* public credentialless "
        "family (Decision AA prefix separation preserves NFR10 contract). "
        "Read-only: NO audit emission (mirrors list_my_share_links + "
        "anonymous share-resolve read-pattern conventions)."
    ),
)
async def resolve_my_share_link(
    token: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    _user_id: uuid.UUID = current_user,
) -> ShareResolveResponse:
    record = await _service(request).resolve(token)
    if record is None:
        raise HTTPException(status_code=404, detail="Share token not found or expired")

    # AC-5 soft-delete check — uniform 404 (NOT a distinct "model gone" detail).
    model = session.exec(
        select(Model).where(Model.id == record.model_id, Model.deleted_at.is_(None))
    ).first()
    if model is None:
        raise HTTPException(status_code=404, detail="Share token not found or expired")

    return ShareResolveResponse(model_id=record.model_id, access="granted")
```

**`apps/web/src/routes/login.tsx`** (replace lines 197-202; add helper above `function Login(...)` at line 18):

```typescript
// Initiative 18 Story 30.1 AC-8 — defend against open-redirect via ?next.
// Accept ONLY same-origin relative paths starting with a single "/" and
// free of control chars. Reject "//evil.com" (protocol-relative), absolute
// URLs, "javascript:" scheme, embedded newlines/null/control bytes.
function _isSafeReturnPath(value: string): boolean {
  if (value.length === 0) return false;
  if (!value.startsWith("/")) return false;
  if (value.startsWith("//")) return false;
  // eslint-disable-next-line no-control-regex
  if (/[\x00-\x1f\x7f]/.test(value)) return false;
  return true;
}

// ... existing component ...

export const Route = createFileRoute("/login")({
  component: Login,
  validateSearch: (raw: Record<string, unknown>): LoginSearch => {
    const out: LoginSearch = {};
    if (typeof raw.next === "string" && _isSafeReturnPath(raw.next)) {
      out.next = raw.next;
    }
    if (raw.reset === "success") out.reset = "success";
    return out;
  },
});
```

**`apps/web/src/routes/login.test.tsx`** (append a new describe block at the end of file):

```typescript
describe("validateSearch open-redirect hardening (Story 30.1 AC-8)", () => {
  const validate = Route.options.validateSearch as (
    raw: Record<string, unknown>,
  ) => { next?: string; reset?: "success" };

  it("RU-1: accepts safe same-origin relative paths starting with /", () => {
    expect(validate({ next: "/share/abc123" })).toEqual({ next: "/share/abc123" });
    expect(validate({ next: "/catalog/xyz" })).toEqual({ next: "/catalog/xyz" });
    expect(validate({ next: "/settings/2fa" })).toEqual({ next: "/settings/2fa" });
    expect(validate({ next: "/" })).toEqual({ next: "/" });
  });

  it("RU-2: drops unsafe next values silently", () => {
    expect(validate({ next: "//evil.com/path" })).toEqual({});
    expect(validate({ next: "https://evil.com" })).toEqual({});
    expect(validate({ next: "http://evil.com" })).toEqual({});
    expect(validate({ next: "javascript:alert(1)" })).toEqual({});
    expect(validate({ next: "\n/path" })).toEqual({});
    expect(validate({ next: "" })).toEqual({});
    expect(validate({ next: "relative-no-slash" })).toEqual({});
    expect(validate({ next: "//attacker.com" })).toEqual({});
    // Preserve unrelated keys
    expect(validate({ next: "//evil.com", reset: "success" })).toEqual({ reset: "success" });
  });
});
```

**`apps/api/tests/test_share_member_router.py`** (append at end of file, after `test_create_share_ttl_capped_at_7_days`):

```python
# ─── Initiative 18 Story 30.1 — share-resolve endpoint coverage ───
# AC-1..AC-11 (resolve_my_share_link). Reuses the existing `client` +
# `seed_two_users_and_model` fixtures. No new fixtures introduced.

_INVALID_404_BODY = '{"detail":"Share token not found or expired"}'


def test_resolve_my_share_link_happy_path_returns_200_with_model_id(
    client, seed_two_users_and_model
):
    """RESOLVE-1: AC-1 + AC-2 + AC-11.

    user_a (admin) creates a token; user_b (member) resolves it; gets 200
    with EXACTLY {model_id, access} keys (AC-11 enumeration-protection).
    """
    user_a, user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    assert r.status_code == 201
    token = r.json()["token"]

    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"model_id", "access"}, (
        f"AC-11 enumeration-protection: extra keys leak token-state. body={body}"
    )
    assert body["model_id"] == str(model_id)
    assert body["access"] == "granted"


def test_resolve_my_share_link_requires_authentication(client, seed_two_users_and_model):
    """RESOLVE-2: AC-3 — anonymous gets 401."""
    user_a, _user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    client.cookies.delete(ACCESS_COOKIE)
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 401
    assert r.json()["detail"] in {"missing_access", "access_expired", "invalid_access"}


def test_resolve_my_share_link_invalid_token_returns_uniform_404(
    client, seed_two_users_and_model
):
    """RESOLVE-3: AC-4 — random-string token returns canonical 404."""
    user_a, _user_b, _mid = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.get(f"/api/me/share-links/{uuid.uuid4().hex}/resolve")
    assert r.status_code == 404
    assert r.text == _INVALID_404_BODY


def test_resolve_my_share_link_expired_token_uniform_404(
    client, isolated_client, seed_two_users_and_model
):
    """RESOLVE-4: AC-4 — Redis TTL elapse returns byte-identical 404 to RESOLVE-3."""
    user_a, user_b, model_id = seed_two_users_and_model
    _c, fake = isolated_client  # fakeredis instance for direct manipulation
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    # Simulate Redis TTL elapse: delete the share-token key directly.
    import anyio
    anyio.run(fake.delete, f"share:token:{token}")

    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 404
    assert r.text == _INVALID_404_BODY  # byte-identical AC-4 enforcement


def test_resolve_my_share_link_revoked_token_uniform_404(
    client, seed_two_users_and_model
):
    """RESOLVE-5: AC-4 — explicitly revoked token returns byte-identical 404."""
    user_a, user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    r = client.delete(f"/api/me/share-links/{token}")
    assert r.status_code == 204

    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 404
    assert r.text == _INVALID_404_BODY


def test_resolve_my_share_link_soft_deleted_model_uniform_404(
    client, seed_two_users_and_model
):
    """RESOLVE-6: AC-5 — soft-deleted model returns byte-identical 404."""
    from datetime import UTC, datetime
    from app.core.db.models import Model

    user_a, user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    with Session(get_engine()) as s:
        m = s.exec(select(Model).where(Model.id == model_id)).one()
        m.deleted_at = datetime.now(UTC)
        s.add(m)
        s.commit()

    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 404
    assert r.text == _INVALID_404_BODY


def test_share_public_router_carries_no_auth_depends_after_init_18():
    """CONTRACT-1: AC-6 NFR10 grep invariant.

    The public /api/share/<token>/* family MUST stay credentialless.
    Substring scan of router.py source — fails closed on accidental
    Depends(current_*) introduction.
    """
    import inspect
    from app.modules.share import router as share_router

    src = inspect.getsource(share_router)
    forbidden = ("current_user", "current_admin", "current_member_or_admin", "current_admin_or_agent")
    hits = [tok for tok in forbidden if tok in src]
    assert hits == [], (
        "NFR18-SHARE-ANON-CONTRACT-1 violated: apps/api/app/modules/share/router.py "
        f"contains auth-dep references {hits}. Move auth-required endpoints to "
        "member_router.py (Decision AA) — see Story 30.1 spec."
    )
```

### Conventions to follow (recap from project-context.md)

- **Annotated dep pattern:** `session: Annotated[Session, Depends(get_session)]` (NOT default-arg style).
- **`Session.exec(select(...))`** (NOT raw SQLAlchemy `Query`).
- **Soft-delete filter:** `Model.deleted_at.is_(None)`.
- **HTTPException copy:** match existing string ("Share token not found or expired") for AC-4 uniformity.
- **Logger namespacing:** N/A for Story 30.1 (no new log emissions — read-only endpoint, no audit).
- **ruff `E,F,W,I,B,UP,SIM,RUF` line-length 100 py312** — run `ruff format` + `ruff check --fix` before commit (T7.2).
- **TypeScript `noUncheckedIndexedAccess`** — `_isSafeReturnPath` already handles `value.length === 0` explicit check; no array indexing in this helper.
- **i18n:** N/A for Story 30.1 (NO new user-visible strings; AC-8 silent drop has no user message).
- **Visual regression:** N/A for Story 30.1 (pure backend + login `validateSearch` hardening; no rendered UI change).
- **Commit message:** conventional commits `fix(api): authenticated share-resolve endpoint + return-URL hardening (Story 30.1, Init 18)` — scope = `api` (primary surface) per project-context.md scope list.

### Project Structure Notes

- All file paths align with existing project structure (project-context.md § Module layout).
- New endpoint placement in `share/member_router.py` follows Init 10 Story 16.3 precedent (member-scoped operations on share-tokens live separately from admin + public surfaces).
- New Pydantic model in `share/models.py` follows the existing convention of co-locating response/request shapes alongside other share models.
- Frontend `_isSafeReturnPath` helper is module-local (not exported, not under `@/lib/`) — single-use, single-file, no need to over-abstract. If a second route ever needs the same logic, promote then.
- No deviation from project structure; no new directories; no new files (only EXTEND existing).

### References

- [Source: `apps/api/app/modules/share/service.py:40-44`] — `ShareService.resolve()` existing method (AC-12 pre-enumeration save).
- [Source: `apps/api/app/modules/share/member_router.py:67-87`] — `revoke_my_share_link` precedent for `current_user` + service.resolve() consumption pattern.
- [Source: `apps/api/app/modules/share/router.py:52-67`] — anonymous `resolve_share` precedent for "Share token not found or expired" copy + soft-delete check shape (AC-4 + AC-5 string-matching source).
- [Source: `apps/api/app/modules/share/admin_router.py:59`] — `_user_id: uuid.UUID = current_admin` precedent for unused-param-with-underscore-prefix (T2.2 lint-friendly variable name).
- [Source: `apps/api/app/core/auth/dependencies.py:77`] — `current_user = Depends(_current_user_dep)` dep export.
- [Source: `apps/api/app/main.py:50-61`] — `_PUBLIC_ROUTES` allowlist (AC-7: new endpoint is NOT added here).
- [Source: `apps/api/tests/test_route_enforcement_gate.py:37-44`] — `_AUTH_DEP_NAMES` registered names (AC-7 verifies `_current_user_dep` already in set).
- [Source: `apps/api/tests/test_share_member_router.py:21-73`] — `client` + `seed_two_users_and_model` fixture pattern (T5 reuse target).
- [Source: `apps/web/src/routes/login.tsx:11-14, 197-203`] — current `LoginSearch` interface + `validateSearch` body (T3 modification target).
- [Source: `apps/web/src/routes/login.test.tsx:237-313`] — existing `?next=/queue` test pattern (T4 placement context).
- [Source: `apps/web/src/shell/AppShell.tsx:38-57`] — anonymous-redirect `pathname + searchStr` → `search: { next }` convention (verifies `_isSafeReturnPath` accepts valid producer-side outputs).
- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 18 Decision AA] — Decision rationale.
- [Source: `_bmad-output/planning-artifacts/prd.md` § Initiative 18 FR18-* + NFR18-*] — Functional + non-functional requirements.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context) via bmad-dev-story skill

### Debug Log References

(populated by dev-story execution)

### Completion Notes List

(populated by dev-story execution)

### File List

(populated by dev-story execution — expected: 5 files modified)

- apps/api/app/modules/share/models.py (EXTEND: ShareResolveResponse)
- apps/api/app/modules/share/member_router.py (EXTEND: resolve_my_share_link handler)
- apps/web/src/routes/login.tsx (MODIFY: _isSafeReturnPath helper + validateSearch body)
- apps/web/src/routes/login.test.tsx (EXTEND: validateSearch hardening describe block, 2 tests)
- apps/api/tests/test_share_member_router.py (EXTEND: 7 new tests for RESOLVE-1..-6 + CONTRACT-1)
