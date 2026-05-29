# Story 31.2: Backend `/api/spools/*` routes + DTOs with cost-data carry-through

Status: done

## Story

As an **authenticated portal user (member or admin)** browsing the new `/spools` route or the landing low-stock card,
I want **three read-only `/api/spools/*` endpoints that project the Redis-cached Spoolman snapshot through stable public DTOs carrying ALL cost-relevant Spoolman fields end-to-end**,
so that **Stories 31.3 + 31.4 land pure FE work against a stable schema, the request path stays bounded by Redis latency (no per-request Spoolman call when the cache is warm), and the future Phase D cost-calc UX has zero schema-backfill cost when triggered**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md` § §4.2 + §4.3 (Story 31.2 row).
Architectural anchor: Decision **AF** (data-model carry-through). Cache topology + leader-elected poll already shipped by Story 31.1 (Decisions AD + AE).
Realizes **FR19-SPOOLS-VIEW-1** + **FR19-DATA-CARRY-1**. NFR19-OBS-1 + NFR19-NETWORK-1 already realized by 31.1 and untouched here.
**Codex tag:** `gpt-5.4-mini` per `[[feedback_codex_model_routing]]` — auth-bearing read-only routes against a LAN-only homelab service; no NFR-SECURITY adjacency; no public-bypass family adjacency; `_PUBLIC_ROUTES` UNTOUCHED.

## Pre-enumeration save (per `[[feedback_scp_pre_enumeration_phase]]` § A)

1. **Files reused (already shipped by 31.1):**
   - `apps/api/app/modules/spools/client.py` — `SpoolmanClient` (httpx wrapper, circuit breaker, observability). The router does NOT call this directly; it only flows through `SpoolsService.get_summary()`, which uses the client for cold-cache fallback only.
   - `apps/api/app/modules/spools/service.py` — `SpoolsService.get_summary() / get_last_success_ts()`. Both are the only service-layer entry points the router calls. NO new methods added in this story.
   - `apps/api/app/modules/spools/models.py` — `SpoolmanSnapshot / SpoolmanSpool / SpoolmanFilament / SpoolmanVendor` internal mirror. The router projects from these into public DTOs; it does NOT mutate the internal models.
   - `apps/api/app/core/auth/dependencies.py` — `current_user` Depends. Mounted on every new route per operator decision 2 (members + admin visible).
   - `apps/api/app/main.py:_PUBLIC_ROUTES` — UNTOUCHED. Story 31.2 mounts only auth-bearing routes.
   - `apps/api/app/router.py` — single `include_router(spools_router)` line append.
2. **New files:**
   - `apps/api/app/modules/spools/schemas.py` — public response DTOs (`VendorView`, `FilamentView`, `SpoolView`, `SpoolsSummaryResponse`). Decision AF cost-data surface.
   - `apps/api/app/modules/spools/router.py` — three GET handlers under prefix `/api/spools`.
   - `apps/api/tests/test_spools_routes.py` — auth + projection + soft-fail + grep-invariant tests.
3. **Modified files:**
   - `apps/api/app/router.py` — single new import + single `include_router(spools_router)` line.
   - `apps/web/src/lib/api-types.ts` — append `VendorView`, `FilamentView`, `SpoolView`, `SpoolsSummaryResponse` interfaces (hand-maintained per file header — there is NO codegen pipeline; the SCP's "api-types.gen.ts" wording is aspirational and predates this discovery).
4. **Test fixtures reused:**
   - `client` / `isolated_client` fixtures in `apps/api/tests/conftest.py` (TestClient + fakeredis).
   - `encode_token(...)` + `c.cookies.set("portal_access", token)` pattern from `test_admin_audit.py:44-46`.
   - `fakeredis.aioredis.FakeRedis()` swap onto `app.state.redis` for cache pre-seeding.
5. **Contracts already enforced (mechanisms named):**
   - **Default-deny** — `apps/api/tests/test_route_enforcement_gate.py` iterates `app.routes` and asserts every `/api/*` route either carries `Depends(current_*)` or appears in `_PUBLIC_ROUTES`. Adding handlers without auth WILL fail this gate. **Mechanism:** route-table introspection at test time.
   - **NFR10 credentialless contract on `/api/share/<token>/*`** — `apps/api/app/modules/share/router.py` MUST stay byte-identical. **Mechanism:** grep invariant in AC-7.
   - **`_PUBLIC_ROUTES` untouched** — Story 31.1 grep invariant carried forward. **Mechanism:** grep invariant in AC-7.
6. **Defensive policies not reversed by this story:** none. This story is pure addition of auth-bearing read-only routes; no Init 6/10/18 contract reversal.

## Cache-topology enumeration (per `[[feedback_scp_pre_enumeration_phase]]` § B)

This is a backend-only story. No React Query keys land here; the FE topology table belongs to Stories 31.3 + 31.4. The Redis cache topology is owned by Story 31.1 (already shipped):

| Backend cache concern | This story (read-only consumer) | Story 31.1 owner (already shipped) |
|---|---|---|
| Cache key                                | reads `spools:summary:v1` via `SpoolsService.get_summary()` | writes `spools:summary:v1` with 30s TTL via `refresh_summary()` |
| Last-success-ts key                      | reads `spools:summary:last-success-ts` via `SpoolsService.get_last_success_ts()` | writes `spools:summary:last-success-ts` (no TTL) on every successful refresh |
| Poll-lock key                            | DOES NOT READ OR WRITE                                  | SETNX `spools:poll-lock` 90s TTL per `refresh_summary()` |
| Cold-cache fallback                      | rides `get_summary()` semantics — returns `None` ⇒ soft-fail response | `get_summary()` falls back to one lock-protected `refresh_summary()` on miss |
| Cache propagation                        | n/a (read-only mirror)                                  | arq cron `poll_spoolman_summary` 60s cadence |

No divergence — Story 31.2 is a pure consumer of the existing topology.

## Acceptance Criteria

### AC-1 — Public DTO module exists at the conventional path with Decision AF cost-data surface

New file `apps/api/app/modules/spools/schemas.py` exposes four Pydantic v2 `BaseModel` classes:

- `class VendorView(BaseModel)` — fields: `id: int`, `name: str`.
- `class FilamentView(BaseModel)` — fields: `id: int`, `name: str`, `vendor_id: int | None`, `vendor_name: str | None`, `material: str | None`, `color_hex: str | None`, `price: float | None`, `weight: float | None`, `spool_weight: float | None`.
- `class SpoolView(BaseModel)` — fields: `id: int`, `filament_id: int`, `price: float | None`, `remaining_weight: float | None`, `initial_weight: float | None`, `used_weight: float | None`, `spool_weight: float | None`, `first_used: datetime | None`, `last_used: datetime | None`, `archived: bool`, `lot_nr: str | None`.
- `class SpoolsSummaryResponse(BaseModel)` — fields: `spools: list[SpoolView]`, `filaments: list[FilamentView]`, `vendors: list[VendorView]`, `fetched_at: datetime | None`, `last_success_ts: datetime | None`.

All field names + types byte-match Decision AF (architecture.md § Initiative 19 Decision AF + this story's pre-enumeration). `model_config = ConfigDict(extra="forbid")` on all four classes — the public surface is strict; schema drift comes from changing the DTO, not from silently accepting extra fields on the wire. Module docstring cites Decision AF + Story 31.2 spec path.

### AC-2 — Three routes mount under `/api/spools` with `Depends(current_user)`

New file `apps/api/app/modules/spools/router.py`:

```python
router = APIRouter(prefix="/api/spools", tags=["spools"])
```

Three handlers, all decorated with the auth dep (operator decision 2 — members + admin visible; NOT `current_admin`):

| Method + Path | Response model | Auth dep |
|---|---|---|
| `GET /api/spools/summary` | `SpoolsSummaryResponse` | `current_user` |
| `GET /api/spools/spools` | `list[SpoolView]` | `current_user` |
| `GET /api/spools/filaments` | `list[FilamentView]` | `current_user` |

Every handler accepts the auth dep via `_user_id: uuid.UUID = current_user` (the user id is not used by the handler body — the parameter exists solely to invoke the dependency); the auth dep MUST be a direct handler parameter so the route-enforcement gate (`apps/api/tests/test_route_enforcement_gate.py`) recognizes it.

The router is wired in `apps/api/app/router.py`:

```python
from app.modules.spools.router import router as spools_router
# ...
api_router.include_router(spools_router)
```

### AC-3 — `GET /api/spools/summary` projects the cached snapshot through public DTOs

Handler reads `SpoolsService.get_summary()` and `SpoolsService.get_last_success_ts()` once each, then:

- **Warm cache** (`get_summary()` returns a non-`None` `SpoolmanSnapshot`): build a `SpoolsSummaryResponse` projecting every internal `SpoolmanSpool`/`SpoolmanFilament`/`SpoolmanVendor` into its `SpoolView`/`FilamentView`/`VendorView` counterpart (field-by-field copy — every Decision AF field carried). `fetched_at = snapshot.fetched_at`. `last_success_ts = await get_last_success_ts()`. Return with HTTP 200.
- **Cold-cache soft-fail** (`get_summary()` returns `None`): return `SpoolsSummaryResponse(spools=[], filaments=[], vendors=[], fetched_at=None, last_success_ts=await get_last_success_ts())` with HTTP 200. The FE distinguishes "data unavailable" from "data empty" via the empty arrays + `last_success_ts` interpretation (if `None`, cold-start failure; if populated but stale, serving prior snapshot). FR19-FAILURE-1 contract — NEVER a 500/503.
- The handler does NOT compute or filter low-stock — that projection lives entirely on the FE (Story 31.4). The backend ships the raw `remaining_weight` field; threshold logic is FE-side per `SPOOLMAN_LOW_STOCK_THRESHOLD_G` env (Story 31.5 documents the env slot).

Service construction inside the handler (per `share_router._service` pattern):

```python
async def _summary(request: Request) -> tuple[SpoolmanSnapshot | None, datetime | None]:
    settings = get_settings()
    async with SpoolmanClient(
        base_url=settings.spoolman_url,
        auth_token=settings.spoolman_auth_token,
    ) as client:
        service = SpoolsService(redis_factory=request.app.state.redis, client=client)
        snapshot = await service.get_summary()
        last_success = await service.get_last_success_ts()
    return snapshot, last_success
```

The `SpoolmanClient` is constructed per request because `get_summary()` may fall through to a single cold-cache `refresh_summary()` call — warm-cache requests never touch the client beyond the cheap `__aexit__` close. The arq poll job already keeps the cache warm in steady state.

### AC-4 — `GET /api/spools/spools` and `/api/spools/filaments` project slices of the same snapshot

Both handlers call the same shared helper (`_summary(request)` above) and return:

- `GET /api/spools/spools` → `[SpoolView.model_validate(s.model_dump()) for s in snapshot.spools]` if snapshot present, else `[]`. HTTP 200.
- `GET /api/spools/filaments` → `[FilamentView.model_validate(f.model_dump()) for f in snapshot.filaments]` if snapshot present, else `[]`. HTTP 200.

No separate Redis read paths — both endpoints ride the canonical `spools:summary:v1` key via `get_summary()`. This preserves cache-coherence: the three endpoints can never disagree on the snapshot they project.

The endpoints expose ARCHIVED spools too (filter is FE-side). The DTO surfaces `archived: bool` so the FE renders/hides per UX preference.

### AC-5 — Frontend type declarations land in `apps/web/src/lib/api-types.ts`

Append (after the existing block) four exported interfaces mirroring AC-1 field-for-field:

```ts
export interface VendorView {
  id: number;
  name: string;
}

export interface FilamentView {
  id: number;
  name: string;
  vendor_id: number | null;
  vendor_name: string | null;
  material: string | null;
  color_hex: string | null;
  price: number | null;
  weight: number | null;
  spool_weight: number | null;
}

export interface SpoolView {
  id: number;
  filament_id: number;
  price: number | null;
  remaining_weight: number | null;
  initial_weight: number | null;
  used_weight: number | null;
  spool_weight: number | null;
  first_used: string | null;  // ISO 8601
  last_used: string | null;   // ISO 8601
  archived: boolean;
  lot_nr: string | null;
}

export interface SpoolsSummaryResponse {
  spools: SpoolView[];
  filaments: FilamentView[];
  vendors: VendorView[];
  fetched_at: string | null;        // ISO 8601
  last_success_ts: string | null;   // ISO 8601
}
```

Block prepended with a single-line comment: `// --- Initiative 19 Story 31.2 (Decision AF) — Spoolman read-only DTOs`. The file's existing header note ("Keep this file in sync by hand when the Pydantic schemas change") remains the source of truth.

### AC-6 — Auth gate enforced uniformly across all three routes

For each of `GET /api/spools/summary`, `GET /api/spools/spools`, `GET /api/spools/filaments`:

- Anonymous request (no `portal_access` cookie) → HTTP 401 `missing_access` (per `_decode` in `app/core/auth/dependencies.py`).
- Invalid token (random string in cookie) → HTTP 401 `invalid_access`.
- Expired token → HTTP 401 `access_expired`.
- Valid member token → HTTP 200.
- Valid admin token → HTTP 200.
- Valid agent token → HTTP 200 (the `agent` role is in `_ALLOWED_ROLES` for `current_user`; agents have legitimate read interest if they ever surface spool data in catalog enrichment).

The route-enforcement gate test (`test_route_enforcement_gate.py`) MUST continue to pass after Story 31.2 lands — the three new routes carry `current_user` Depends, so the gate's allowlist DOES NOT need extension (and `_PUBLIC_ROUTES` MUST NOT be extended — see AC-7).

### AC-7 — Grep invariants: `_PUBLIC_ROUTES` + `share/router.py` + `share/member_router.py` byte-identical to pre-31.2 state

- `git diff main -- apps/api/app/main.py` shows zero changes to the `_PUBLIC_ROUTES` tuple. (`main.py` itself is not edited by Story 31.2.)
- `git diff main -- apps/api/app/modules/share/router.py` shows zero changes. NFR10 credentialless contract on `/api/share/<token>/*` preserved.
- `git diff main -- apps/api/app/modules/share/member_router.py` shows zero changes.
- `git diff main -- apps/api/app/modules/share/admin_router.py` shows zero changes.
- No `Depends(current_*)` on any `/api/share/<token>/*` route (re-asserted via the pytest grep test — TEST-7).

### AC-8 — Test plan: pytest coverage in `apps/api/tests/test_spools_routes.py`

New file ships these cases:

- **TEST-1** `test_summary_anonymous_returns_401` — GET `/api/spools/summary` without cookie → 401.
- **TEST-2** `test_spools_anonymous_returns_401` — GET `/api/spools/spools` without cookie → 401.
- **TEST-3** `test_filaments_anonymous_returns_401` — GET `/api/spools/filaments` without cookie → 401.
- **TEST-4** `test_summary_member_returns_200_with_cached_payload` — pre-seed `spools:summary:v1` with a valid `SpoolmanSnapshot.model_dump_json()` (2 spools, 1 filament, 1 vendor); seed `spools:summary:last-success-ts` with an ISO8601 timestamp; GET `/api/spools/summary` with a member cookie → 200; body matches `SpoolsSummaryResponse` shape (length checks + selected field byte-match).
- **TEST-5** `test_summary_carries_cost_relevant_fields_end_to_end` — pre-seed cache where the seed spool has `price=42.5`, `remaining_weight=850.0`, `initial_weight=1000.0`, `spool_weight=200.0`, `lot_nr="ABC123"`, and filament has `price=99.9`, `weight=1000.0`, `spool_weight=200.0`. GET summary as member, assert every one of those fields appears verbatim in the response body. Decision AF carry-through proof.
- **TEST-6** `test_summary_cold_cache_returns_200_with_empty_arrays` — empty fakeredis (no cache + no last-success-ts); patch `SpoolmanClient._get` to raise `httpx.ConnectError` so the cold-cache fallback fails too; GET summary as member → 200; body = `{"spools": [], "filaments": [], "vendors": [], "fetched_at": null, "last_success_ts": null}`. FR19-FAILURE-1 contract proven.
- **TEST-7** `test_summary_warm_cache_with_old_last_success_ts_still_returns_200` — seed cache + seed `last_success_ts` with a 5-minute-old ISO8601 value; patch the client to raise (simulating Spoolman down, but cache still warm — Story 31.1 TEST-7 sibling). GET summary as member → 200; response carries the 5-minute-old `last_success_ts`. Stale-serve contract.
- **TEST-8** `test_spools_member_returns_200_with_projected_list` — same seed as TEST-4; GET `/api/spools/spools` as member → 200; body length matches seeded spool count; every cost-relevant field present per element.
- **TEST-9** `test_filaments_member_returns_200_with_projected_list` — same seed; GET `/api/spools/filaments` as member → 200; body length matches; every cost-relevant field present per element.
- **TEST-10** `test_admin_token_also_authorized` — admin cookie on `/api/spools/summary` → 200. Operator decision 2 enforcement.
- **TEST-11** `test_invalid_token_returns_401` — set `portal_access=garbage` cookie; GET summary → 401 `invalid_access`.
- **TEST-12** `test_share_router_files_byte_identical_to_main` — read `apps/api/app/modules/share/router.py` content + assert no `Depends(current_user|admin|member_or_admin)` decorator appears on any handler whose path starts with `/api/share/<token>`. NFR10 grep invariant. (Implementation note: load source file as text, regex for `@router\.(get|post|put|delete)\("/<token>` followed within 30 lines by any `current_user|current_admin|current_member_or_admin` symbol; assert zero matches.)
- **TEST-13** `test_public_routes_tuple_unchanged` — import `_PUBLIC_ROUTES`, assert it equals the byte-identical tuple from pre-31.2 (literal asserts):
  ```python
  assert _PUBLIC_ROUTES == (
      "/api/health",
      "/api/auth/login",
      "/api/auth/logout",
      "/api/auth/refresh",
      "/api/auth/register",
      "/api/auth/2fa/verify",
      "/api/auth/password-reset",
      "/api/share/{token}",
      "/api/share/{token}/files",
      "/api/share/{token}/files/{file_id}/content",
  )
  ```

### AC-9 — Determinism + observability gates

- 3× consecutive `apps/api/.venv/bin/pytest apps/api/tests/test_spools_routes.py -q` runs return identical pass counts (NFR19-DETERMINISM-1 microcosm — the full backend suite continues to be checked in dev-story closeout).
- The router does NOT emit new structured log records (read-only handlers; cache hits are silent — the `spools.poll.*` family already covers Spoolman client telemetry). NFR19-OBS-1 is owned by 31.1's client.
- `external_service=spoolman` label MUST still appear in every Spoolman client log on the cold-cache fallback path (`get_summary()` → `refresh_summary()` → `_get()`); 31.1 already guarantees this and TEST-6 indirectly exercises that path.

### AC-10 — `_PUBLIC_ROUTES` allowlist UNTOUCHED

`apps/api/app/main.py:_PUBLIC_ROUTES` is byte-identical pre- and post-Story-31.2. Story 31.2 mounts only auth-bearing routes; no public-bypass extension. Grep invariant validated by TEST-13 + AC-7.

## Magic-constant contracts (per `[[feedback_scp_pre_enumeration_phase]]` § C)

Story 31.2 introduces ZERO new numeric/time/size literals. All previously-pinned literals (httpx 5s timeout, circuit-breaker 3/30s, Redis 30s TTL, SETNX 90s lock expiry, arq 60s cadence) remain owned by Story 31.1's `client.py` + `service.py` + `workers/spoolman_poll.py` with inline `because "..."` contract comments. No new contract pointers required.

## Tasks / Subtasks

- [ ] **T1** (AC-1) — Author `apps/api/app/modules/spools/schemas.py`
  - [ ] T1.1 Create the file with module docstring citing Decision AF + Story 31.2.
  - [ ] T1.2 Implement `VendorView`, `FilamentView`, `SpoolView`, `SpoolsSummaryResponse` per AC-1 field list. All four classes set `model_config = ConfigDict(extra="forbid")`.

- [ ] **T2** (AC-2 + AC-3 + AC-4) — Author `apps/api/app/modules/spools/router.py`
  - [ ] T2.1 Create the file with module docstring referencing Decision AF + Story 31.2 spec path.
  - [ ] T2.2 Define `_summary(request)` helper that constructs `SpoolmanClient(...)` + `SpoolsService(...)`, calls `get_summary()` + `get_last_success_ts()`, returns `(snapshot, last_success)` tuple.
  - [ ] T2.3 Implement the three handlers — each accepts `_user_id: uuid.UUID = current_user` and `request: Request`. Build the response by field-for-field projection. Return `SpoolsSummaryResponse` / `list[SpoolView]` / `list[FilamentView]`.
  - [ ] T2.4 On `snapshot is None`, return the soft-fail response per AC-3 (empty arrays for `/summary`; empty list for `/spools` + `/filaments`).

- [ ] **T3** (AC-2 wire-in) — Wire the new router into `apps/api/app/router.py`
  - [ ] T3.1 Add `from app.modules.spools.router import router as spools_router` (alphabetical: between `share_router` and `sot_admin_router` imports; place new import in alphabetical position).
  - [ ] T3.2 Append `api_router.include_router(spools_router)` to the bottom of the include list.

- [ ] **T4** (AC-5) — Append TypeScript types to `apps/web/src/lib/api-types.ts`
  - [ ] T4.1 Append a `// --- Initiative 19 Story 31.2 (Decision AF) — Spoolman read-only DTOs` separator + the four interfaces verbatim per AC-5.

- [ ] **T5** (AC-8 + AC-9) — Author `apps/api/tests/test_spools_routes.py`
  - [ ] T5.1 Create the file. Import `pytest`, `httpx`, `fakeredis.aioredis`, `app.core.auth.jwt.encode_token`, `app.main.create_app`, `app.modules.spools.models.SpoolmanSnapshot`, `app.modules.spools.client`, plus the seeded user UUIDs.
  - [ ] T5.2 Per-test pattern: build a `create_app()` instance, swap `app.state.redis` to a `MagicMock(get=lambda: fake)` factory (mirrors `isolated_client` shape), enter `with TestClient(app) as c:`, set the appropriate auth cookie via `encode_token(...)` + `c.cookies.set("portal_access", token)`. Per-test fakeredis instance to avoid leakage.
  - [ ] T5.3 Implement TEST-1 through TEST-13 verbatim per AC-8.
  - [ ] T5.4 For TEST-6 + TEST-7 (cache-miss + client error), patch `app.modules.spools.client.SpoolmanClient._get` to raise `httpx.ConnectError("simulated outage")` via `monkeypatch.setattr`.

- [ ] **T6** (AC-7) — Cross-cutting grep invariants
  - [ ] T6.1 Run `git diff main -- apps/api/app/main.py apps/api/app/modules/share/` and confirm zero diff against the four files named in AC-7.
  - [ ] T6.2 Document the invariant outcomes in the Dev Agent Record below.

- [ ] **T7** (gates) — Pre-merge gate execution
  - [ ] T7.1 `ruff format --check apps/api && ruff check apps/api` → PASS.
  - [ ] T7.2 `apps/api/.venv/bin/pytest apps/api/tests/test_spools_routes.py -q` → PASS (13 cases).
  - [ ] T7.3 `apps/api/.venv/bin/pytest apps/api/tests/test_route_enforcement_gate.py -q` → PASS (route-enforcement gate continues to recognize all three new routes as `current_user`-bearing).
  - [ ] T7.4 Full backend suite: `apps/api/.venv/bin/pytest -q` → PASS counts equal-or-better than pre-31.2 baseline (938 passed / 1 skipped + the 13 new cases = 951 expected).
  - [ ] T7.5 3× determinism: `for i in 1 2 3; do apps/api/.venv/bin/pytest apps/api/tests/test_spools_routes.py -q; done` → identical pass counts.
  - [ ] T7.6 `npm run typecheck` on `apps/web/` (after T4.1) → PASS — confirms the new TS interfaces are syntactically valid and do not conflict with existing exports.

- [ ] **T8** (close-out) — Branch hygiene + commit message contract
  - [ ] T8.1 Commit subject: `feat(api): Spoolman /api/spools/* routes + DTO cost-carry (Story 31.2, Init 19)`.
  - [ ] T8.2 Commit body cites the spec path + Story 31.1 OD8 close-out reference (no new OD8 attestation in 31.2; the LAN-only bind was already verified during Story 31.1 and 31.2 introduces no new outbound surface).
  - [ ] T8.3 ff-merge to `main` per AGENTS.md branching contract; delete the branch post-merge; push origin main; auto-deploy via `infra/scripts/deploy.sh` lands on `.190`.

## Dev Agent Record

### Code-side gates (filled by dev-story execution)

- ruff format + check on apps/api: PASS
- pytest tests/test_spools_routes.py: 15 passed, 32 warnings
- pytest tests/test_route_enforcement_gate.py: 3 passed
- pytest full backend: 953 passed / 1 skipped (TEST-LIVE-1 env-gated from Story 31.1; zero new warnings introduced)
- 3× determinism on test_spools_routes.py: identical `15 passed, 32 warnings`
- npm run typecheck (apps/web): PASS

### Grep invariants (filled by dev-story execution)

- `_PUBLIC_ROUTES` byte-diff: zero diff on `apps/api/app/main.py` against `origin/main` (Story 31.2 does NOT touch `main.py`).
- `share/router.py` byte-diff: zero diff against `origin/main`.
- `share/member_router.py` byte-diff: zero diff against `origin/main`.
- `share/admin_router.py` byte-diff: zero diff against `origin/main`.

### Review Findings (filled by code-review execution)

**Reviewer routing deviation:** native Codex CLI (`/home/ezop/.local/bin/codex review --commit 0e2fec6`) hung on MCP transport after a 180s bounded timeout — same failure mode as Story 31.1 round-7. Per AGENTS.md § Autonomous development mode, Story 31.2 disclaims NFR-SECURITY adjacency (Story line 14 + Pre-enumeration save #5 + #6: auth-bearing read-only routes against a LAN-only homelab service; no public-bypass family adjacency; `_PUBLIC_ROUTES` untouched; no auth boundary change). Labeled fallback used: Claude Sonnet 4.6 delegate (via `feature-dev:code-reviewer` sub-agent, labeled honestly in the agent's verdict — no native-Codex impersonation).

**Verdict (single round):** APPROVED — no Critical, no Important, no Minor findings.

Reviewer scrutiny areas walked (all pass):

1. Cache-coherence across the three handlers — within a single request the snapshot is read once and projected locally; the inter-request 30s/60s window is the explicitly accepted trade-off, documented in the spec.
2. Warm-cache path correctly avoids touching the httpx layer (only cheap `__aenter__`/`__aexit__` on `httpx.AsyncClient`).
3. Cold-cache soft-fail propagation: `refresh_summary()` → broad `except` → `None`, then `_project_summary(None, last_success)` returns 200 + empty arrays per FR19-FAILURE-1.
4. `async with SpoolmanClient(...)` resource lifetime is leak-free under handler exceptions.
5. `model_dump()` → `model_validate()` roundtrip preserves every Decision AF field; internal `extra="ignore"` + public `extra="forbid"` are correctly composed.
6. Auth gate: every handler carries `_user_id: uuid.UUID = current_user`; route-enforcement gate recognizes the dependency; no sub-app/middleware bypass.
7. `asgi_app` fixture isolation: per-test fakeredis + per-test tmp SQLite + `cache_clear` on entry+exit.
8. Story 31.1 byte-pinned cache keys (`spools:summary:v1`, `spools:summary:last-success-ts`, `spools:poll-lock`) untouched.
9. TypeScript interfaces field-for-field match the Python DTOs (name + nullability + type).
10. Sprint-status YAML structurally intact.

Triage: 0 decision-needed, 0 patch, 0 deferred, 0 dismissed. Status flipped review → done.

## Out of scope

- FE route impl (`/spools` page) — Story 31.3.
- Landing low-stock card — Story 31.4.
- i18n keys + ops doc + visual baseline regen — Story 31.5.
- Spoolman writes (mutation surface) — MVP-D Phase C indefinitely deferred per operator decision 4.
- Cost calculator UX — Phase D deferred per Decision AF.
- Low-stock threshold env (`SPOOLMAN_LOW_STOCK_THRESHOLD_G`) — Story 31.5 owns the env slot; this story's `remaining_weight` is the raw input.
- New rate-limit scope on `/api/spools/*` — none. Cookie-bound authenticated reads ride the existing implicit per-user pacing; no public-facing burst surface.
- Audit emission on read endpoints — not done (mirrors `/api/admin/audit` GET + `/api/me/share-links` GET conventions).
