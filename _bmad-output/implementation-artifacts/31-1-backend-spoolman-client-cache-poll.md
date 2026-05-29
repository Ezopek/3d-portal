# Story 31.1: Backend Spoolman client + Redis cache + arq poll job + env config

Status: done

## Story

As an **autonomous portal backend** that needs to mirror the homelab Spoolman inventory at `.190:7912` without coupling request-path latency to a third-party service,
I want **an isolated `apps/api/app/modules/spools/` package that wraps Spoolman's `/api/v1/*` over `httpx.AsyncClient`, caches the upstream snapshot in Redis under a single canonical key with a leader-elected arq cron, and surfaces structured-log + OTel observability tagged `external_service=spoolman`**,
so that **Story 31.2 can mount the `/api/spools/*` routes against a stable in-process service layer, the landing low-stock card (Story 31.4) and `/spools` index (Story 31.3) stay fresh within a 60s budget without hammering Spoolman, and any Spoolman outage degrades to the explicit soft-fail UX (FR19-FAILURE-1) instead of cascading 500s through the request path**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md` § §4.2 + §4.3 + §4.4 (Story 31.1 entry).
Architectural anchors: Decision **AD** (cache topology + poll cadence + leader-election + observability) and Decision **AE** (network transport — internal docker network + configs-side coordination + P4a fallback) per `architecture.md` § Initiative 19.
Realizes **FR19-CACHE-1**, **NFR19-NETWORK-1**, **NFR19-OBS-1** (and lays the cache foundation Story 31.2 reuses for FR19-DATA-CARRY-1 + FR19-SPOOLS-VIEW-1).
**Codex tag:** `gpt-5.4-mini` per `[[feedback_codex_model_routing]]` — read-only outbound HTTP to a LAN-only homelab service; no NFR-SECURITY adjacency; no public-bypass family adjacency (`_PUBLIC_ROUTES` untouched); no auth boundary change.

## Acceptance Criteria

### AC-1 — Module skeleton exists at the conventional path

A new package `apps/api/app/modules/spools/` ships with `__init__.py` (empty re-export module), `client.py` (httpx wrapper), `service.py` (cache + poll orchestration), and `models.py` (internal Pydantic mirror of Spoolman's response shape — full Decision AF cost-relevant field surface; public response DTOs land in Story 31.2 against this same internal schema). No `router.py` in this story (Story 31.2 owns route mounting). The package directory mirrors the layout of existing modules (`apps/api/app/modules/share/`, `apps/api/app/modules/admin/`).

### AC-2 — Two env slots present in `Settings` with documented defaults

`apps/api/app/core/config.py` `Settings` gains exactly two new fields:

| Field | Type | Default | Notes |
|---|---|---|---|
| `spoolman_url` | `str` | `"http://spoolman:8000"` | Decision AE primary topology P4b — internal docker network resolves the `spoolman` hostname. P4a fallback: operator overrides to `http://localhost:7912` (one-line transitional posture if the configs-side PR slips). |
| `spoolman_auth_token` | `str` | `""` | Reserved for future P3d Spoolman auth (Phase C trigger; per operator decision 4, NOT triggered by MVP-A scope). Carried in MVP-A so the `Authorization: Bearer …` wiring lands once and the env-driven swap stays a one-file change. Empty value disables the header (client sends no Authorization on empty token). |

`infra/env.example` documents both slots with a comment referencing Decision AE + the configs-side network precondition. **No** `SPOOLMAN_LOW_STOCK_THRESHOLD_G` env slot in this story — that field is Story 31.2's surface (threshold-aware low-stock filtering lives in the route projection, not in the cache mirror).

### AC-3 — `SpoolmanClient` wraps `httpx.AsyncClient` with timeout + Authorization-on-non-empty-token + observability tag

`apps/api/app/modules/spools/client.py` exposes `class SpoolmanClient`:

- Constructed from `Settings` (base URL = `settings.spoolman_url.rstrip('/')`; token = `settings.spoolman_auth_token`).
- Three async methods: `list_spools()`, `list_filaments()`, `list_vendors()` returning `list[SpoolmanSpool]` / `list[SpoolmanFilament]` / `list[SpoolmanVendor]` parsed from `GET /api/v1/spool`, `/api/v1/filament`, `/api/v1/vendor`.
- `httpx.AsyncClient(timeout=httpx.Timeout(5.0))` per Decision AD magic-constant contract (see AC-7).
- `Authorization: Bearer <token>` header sent **only** when `settings.spoolman_auth_token` is non-empty (MVP-A default leaves it off).
- Structured logging on every call (AC-6) + OTel span wrapping the request (AC-6).
- Response bodies parsed into internal Pydantic models (AC-5); raw JSON NEVER logged at INFO (AC-6 + brainstorm anti-pattern 8).

### AC-4 — `SpoolsService` exposes the cache topology contract from Decision AD

`apps/api/app/modules/spools/service.py` exposes `class SpoolsService` constructed from `(RedisFactory, SpoolmanClient)` with three methods:

- `async def get_summary() -> SpoolmanSnapshot | None` — read path. Returns the cached snapshot deserialized from `spools:summary:v1` if present; falls through to a single lock-protected live fetch on cold-cache miss (calls `refresh_summary()` once); returns `None` only when both the cache is empty AND the live fetch raises (FR19-FAILURE-1 cold-start-with-Spoolman-down — the route layer in Story 31.2 + UI layer in Stories 31.3/31.4 render the explicit "Spoolman unavailable" empty state on `None`).
- `async def get_last_success_ts() -> datetime | None` — sibling read; returns the parsed `spools:summary:last-success-ts` ISO8601 value or `None` if the key is missing. Powers the "Last updated HH:MM (Xm ago)" FE indicator (FR19-FAILURE-1).
- `async def refresh_summary() -> SpoolmanSnapshot | None` — write path. Acquires Redis SETNX `spools:poll-lock` with 90s expiry (AC-9). On lock acquisition, calls all three client methods (`list_spools` / `list_filaments` / `list_vendors`), assembles a `SpoolmanSnapshot`, JSON-encodes it via the Pydantic model, writes to `spools:summary:v1` with 30s TTL, writes the current UTC ISO8601 to `spools:summary:last-success-ts` (no TTL — persists across cache rotations so the soft-fail indicator can compute `Xm ago` from arbitrary delays). On lock-already-held, returns `None` without raising (idempotent — another worker is refreshing). On client failure with cache empty, returns `None`; on client failure with cache populated, leaves the existing cache + `last-success-ts` untouched (Decision AD failure semantics).

The exact Redis keys are **byte-pinned** in this AC: `spools:summary:v1`, `spools:summary:last-success-ts`, `spools:poll-lock`. A change to any of these strings requires a Sprint Change Proposal — they are the contract surface every downstream story and every operational runbook query.

### AC-5 — Internal Pydantic models mirror Spoolman's response shape with the full Decision AF field surface

`apps/api/app/modules/spools/models.py` exposes four classes:

- `class SpoolmanFilament(BaseModel)` — fields: `id: int`, `name: str`, `vendor_id: int | None`, `vendor_name: str | None`, `material: str | None`, `color_hex: str | None`, `price: float | None`, `weight: float | None` (grams, full-spool initial weight), `spool_weight: float | None` (grams, empty cardboard).
- `class SpoolmanSpool(BaseModel)` — fields: `id: int`, `filament_id: int`, `price: float | None` (per-spool override), `remaining_weight: float | None`, `initial_weight: float | None`, `used_weight: float | None`, `spool_weight: float | None`, `first_used: datetime | None`, `last_used: datetime | None`, `archived: bool`, `lot_nr: str | None`.
- `class SpoolmanVendor(BaseModel)` — fields: `id: int`, `name: str`.
- `class SpoolmanSnapshot(BaseModel)` — fields: `spools: list[SpoolmanSpool]`, `filaments: list[SpoolmanFilament]`, `vendors: list[SpoolmanVendor]`, `fetched_at: datetime`. JSON-encodes losslessly via `model_dump_json()`; deserializes via `model_validate_json()`.

All fields use `model_config = ConfigDict(extra="ignore")` so additional Spoolman 0.23.1 → 0.24.x fields do not crash the parser on schema drift. The internal models are **not** exposed via the OpenAPI surface — they are the cache schema, not the HTTP response schema. Story 31.2 ships the public `SpoolView` / `FilamentView` response DTOs that project from these internal models with the full Decision AF cost-relevant field surface intact.

### AC-6 — Observability: every Spoolman client call carries `external_service=spoolman` + OTel span + GlitchTip breadcrumb category

Each successful or failed Spoolman HTTP call emits exactly one structured log record (Python `logging` + `extra={...}` per the project's `JsonFormatter` convention at `apps/api/app/core/logging.py`) with these labels:

```python
logger.info(
    "spools.client.call",
    extra={
        "event.action": "spools.client.call",
        "labels.external_service": "spoolman",
        "labels.endpoint": endpoint,           # e.g. "GET /api/v1/spool"
        "labels.duration_ms": int(elapsed_ms),
        "labels.status_code": response_status, # 0 if connect-error before status
        "labels.lock_acquired": lock_held,     # bool; only on refresh path, else omitted
        "labels.entity_count": count,          # parsed entity count; omitted on error
    },
)
```

On failure paths the record level is `logger.warning(...)` and the message becomes `"spools.client.error"` with `labels.error_class` (the exception class name) instead of `labels.entity_count`. Response bodies are **never** logged at INFO — only entity counts (per Decision AD § Observability + brainstorm anti-pattern 8).

Every httpx call is also wrapped in an OTel span named `spoolman.client.<endpoint>` (e.g. `spoolman.client.GET_/api/v1/spool` — slashes preserved in the span name for grep continuity with the structured log endpoint label) via the existing `opentelemetry.trace.get_tracer(__name__).start_as_current_span(...)` pattern. The span name is the same on success and failure; span status is set to ERROR on exceptions.

Sentry/GlitchTip breadcrumbs are emitted at category `spoolman.client` via `sentry_sdk.add_breadcrumb(category="spoolman.client", message=endpoint, level="info"|"warning", data={"duration_ms": ..., "status_code": ...})`. The breadcrumb path is best-effort (no-op when the Sentry SDK is not initialized; `sentry_sdk.add_breadcrumb` already handles that internally).

### AC-7 — Magic-constant contracts (per [[feedback_scp_pre_enumeration_phase]] § C — every literal points to the contract it serves, not to a peer usage)

Each literal below appears in code with a single-line comment containing the `because "…"` justification. Comments are mandatory — the reviewer should be able to grep the source and find the contract pointer beside every magic number.

| Literal | Location | Contract pointed to |
|---|---|---|
| `5.0` (httpx timeout, seconds) | `client.py` constructor | because **"Spoolman is LAN-only on `.190`, typical response ~50ms; 5s upper bound flags genuine outage rather than transient latency — Decision AD"** |
| `3` (consecutive failures → circuit open) | `client.py` circuit-breaker state | because **"3 consecutive errors signal real outage rather than transient blip per Decision AD; matches typical resilience-pattern band"** |
| `30` (circuit-breaker open seconds) | `client.py` circuit-breaker state | because **"30s open window matches the `spools:summary:v1` Redis TTL so a fresh probe naturally retries when cache would expire anyway — Decision AD"** |
| `30` (Redis TTL on `spools:summary:v1`, seconds) | `service.py` `refresh_summary()` | because **"upper bound on stale snapshot served from Redis; poll runs every 60s but a fresh request within the 30-60s gap still serves the slightly-staler cached value rather than triggering a synchronous fetch in the request path — Decision AD"** |
| `90` (SETNX `spools:poll-lock` expiry, seconds) | `service.py` `refresh_summary()` | because **"worst-case Spoolman refresh latency is ~5s × 3 entity types + serialization headroom; 90s comfortably covers stuck-poll scenarios without holding the lock past the next 60s poll interval — Decision AD"** |
| `60` (arq cron cadence, seconds) | `workers/__init__.py` `cron_jobs` entry | because **"FR19-CACHE-1 low-stock freshness budget is 60s; sub-minute polling would burn LAN-only egress with no UX gain — Decision AD"** |

`spools:summary:v1` / `spools:summary:last-success-ts` / `spools:poll-lock` literals are also commented in code as: because **"contract surface — change requires SCP per AC-4"**.

The `staleTime: 60_000` / `gcTime: 5 * 60_000` FE contracts live in Stories 31.3 + 31.4; Story 31.1 only enforces the backend half.

### AC-8 — arq cron `poll_spoolman_summary` registered in the api-arq queue every 60s

A new file `apps/api/app/workers/spoolman_poll.py` defines:

```python
async def poll_spoolman_summary(ctx: dict) -> int:
    """arq task: refresh the Spoolman snapshot. Returns 1 if this worker
    acquired the SETNX lock and wrote a new snapshot; 0 if another worker
    holds the lock (idempotent skip)."""
    ...
```

`apps/api/app/workers/__init__.py` is amended:

- `functions: ClassVar[list]` gains `poll_spoolman_summary`.
- `cron_jobs: ClassVar[list]` gains `cron(poll_spoolman_summary, second={0})` — runs at second :00 every minute (≈60s cadence). The literal `{0}` is justified inline per AC-7's cron-cadence contract pointer.

The task runs on the existing api-arq-worker container (`API_QUEUE_NAME = "arq:api"` — same queue as `cleanup_refresh_tokens` and `generate_thumbnail`; the render-worker queue is left alone per AGENTS.md § Worker depends on `portal-api` editable).

The cron entry point constructs a fresh `SpoolsService` per tick from a request-scoped `RedisFactory` + `SpoolmanClient` (NOT a process-global instance — keeps the worker stateless across ticks; the SETNX lock guarantees single-poller semantics across multiple worker replicas).

### AC-9 — Single-poller SETNX leader-election survives concurrent worker contention

When two `refresh_summary()` calls run concurrently (test fixture spawns two `asyncio.create_task(service.refresh_summary())`), exactly one acquires `spools:poll-lock` (SETNX returns True) and writes the snapshot; the other observes SETNX returning False and returns `None` without calling any client method and without raising. Lock TTL is 90s (AC-7); the winner releases the lock on completion via `DELETE` (best-effort — TTL covers the case where the worker crashes mid-poll). Coverage: see TEST-3 in AC-10.

### AC-10 — Test plan: pytest httpx-mock unit suite + ONE env-gated `SPOOLMAN_LIVE_TEST=1` integration

New file `apps/api/tests/test_spools.py` ships these cases:

- **TEST-1** `test_client_list_spools_happy_path_parses_response` — mocks `GET /api/v1/spool` via `httpx.MockTransport` returning a 3-spool fixture; asserts `SpoolmanClient.list_spools()` returns 3 `SpoolmanSpool` instances with the full Decision AF cost-relevant field surface populated (`remaining_weight`, `price`, `lot_nr`, etc.).
- **TEST-2** `test_client_authorization_header_omitted_when_token_empty` — mocks the transport with a request-inspector; asserts `Authorization` header is **absent** when `settings.spoolman_auth_token == ""`; assert present + correctly formatted when token is non-empty.
- **TEST-3** `test_service_refresh_summary_under_lock_contention_runs_once` — two parallel `asyncio.create_task(service.refresh_summary())` calls against a `fakeredis` instance + a mock client that records `list_spools` invocation count; asserts the mock client is called **exactly once** across the two tasks; asserts exactly one task returns a non-`None` snapshot, the other returns `None`. AC-9 enforcement.
- **TEST-4** `test_service_get_summary_cache_warm_skips_client` — pre-seeds `spools:summary:v1` with a valid `SpoolmanSnapshot.model_dump_json()`; asserts `service.get_summary()` returns the deserialized snapshot **without** calling any client method (mock client has `list_spools.assert_not_called()`).
- **TEST-5** `test_service_get_summary_cache_miss_triggers_single_live_fetch` — empty Redis + mock client returning a valid snapshot; asserts `service.get_summary()` returns the snapshot, the cache key is now populated, `spools:summary:last-success-ts` is populated, and mock client `list_spools` was called once.
- **TEST-6** `test_service_get_summary_cache_empty_and_spoolman_down_returns_none` — empty Redis + mock client raises `httpx.ConnectError` on every method; asserts `service.get_summary()` returns `None` and does **not** raise; asserts the cache stays empty (no partial snapshot written); asserts `spools:summary:last-success-ts` stays absent. FR19-FAILURE-1 cold-start contract.
- **TEST-7** `test_service_get_summary_cache_warm_and_spoolman_down_serves_stale` — pre-seeds cache + sibling `last-success-ts` with a value 5 minutes old; mock client raises on refresh; asserts `service.get_summary()` returns the cached snapshot and `service.get_last_success_ts()` returns the original 5-minutes-old timestamp (cache + sibling untouched on failure). FR19-FAILURE-1 stale-serve contract.
- **TEST-8** `test_client_circuit_breaker_opens_after_three_failures` — mock client raises on three consecutive calls; asserts the fourth call short-circuits (no HTTP attempt — mock transport records 3 hits, not 4); asserts the breaker reopens after the 30s window elapses (test fast-forwards via `monkeypatch.setattr(time, ...)`).
- **TEST-9** `test_observability_labels_present_on_client_log` — patches the module logger; calls `SpoolmanClient.list_spools()` with a successful mock; asserts the captured log record has `extra["labels.external_service"] == "spoolman"`, `extra["labels.endpoint"] == "GET /api/v1/spool"`, `extra["labels.duration_ms"]` is `int`, `extra["labels.entity_count"]` matches the fixture spool count. AC-6 enforcement.
- **TEST-10** `test_observability_response_body_not_logged_at_info` — captures all log records emitted during a `list_spools()` happy path; asserts no captured record's message field nor any `extra` value contains the verbatim spool name or color hex from the fixture. Brainstorm anti-pattern 8 + Decision AD enforcement.
- **TEST-11** `test_arq_cron_poll_spoolman_summary_registered_at_60s_cadence` — imports `apps.workers.WorkerSettings`; asserts `poll_spoolman_summary` is in `WorkerSettings.functions` and the `cron_jobs` entry for it has `second={0}` (60s cadence). AC-8 enforcement.

Plus **ONE env-gated live integration test**:

- **TEST-LIVE-1** `test_spoolman_live_smoke_contract` — gated via `@pytest.mark.skipif(os.environ.get("SPOOLMAN_LIVE_TEST") != "1", reason="live Spoolman not reachable; opt in via SPOOLMAN_LIVE_TEST=1")`. Default-skipped in CI + autonomous runs. When enabled: constructs a real `SpoolmanClient` pointing at `settings.spoolman_url` (operator overrides to `http://localhost:7912` for laptop runs), calls `list_spools()` + `list_filaments()` + `list_vendors()`, asserts each returns a non-empty list and the Pydantic parse succeeds (contract pinning against the real Spoolman 0.23.1 response shape). This is the only test that hits the live homelab service; CI and `npm run check-all` leave it skipped.

### AC-11 — Pre-merge precondition: configs-side Spoolman bind-address verification (OD8 close-out, NOT a 3d-portal commit)

Before this story merges to `main`, the configs-side operator verifies that `~/repos/configs/docker-compose-recipes/spoolman.yml` binds Spoolman to the **LAN interface only** (`192.168.2.190:7912:8000`) rather than the Docker default all-interfaces exposure. Operator decision (recorded 2026-05-29): Spoolman MUST remain reachable from the LAN because the printer pushes filament-usage updates live and the operator + phone consume Spoolman directly on the LAN — a strict `127.0.0.1`-only bind is therefore NOT the target posture. The acceptable posture is an explicit LAN-interface-only bind (`HostIp: "192.168.2.190"`); the rejected posture is the Docker default all-interfaces exposure (`HostIp: "0.0.0.0"` and/or `HostIp: "::"`), which leaves Spoolman reachable on every host interface including any non-LAN paths the host may grow.

Verification recipe (executed on `.190` by the operator; documented in the Story 31.5 ops-doc addendum, NOT in this story):

```bash
# On .190 host, AFTER the configs-side compose edit + redeploy:
docker inspect spoolman --format '{{json .NetworkSettings.Ports}}' | jq
# Expect: "8000/tcp": [ { "HostIp": "192.168.2.190", "HostPort": "7912" } ]
# REJECT:  HostIp: "0.0.0.0" or HostIp: "::" (Docker default all-interface exposure).
```

This precondition is **not enforced by a 3d-portal pytest gate** (it lives in the configs repo's compose file), but the Story 31.1 dev-story commit message **must** include the line `OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)` once the verification has been confirmed by the operator. The OD8 audit trail lives in the SCP frontmatter + this story's commit message.

The configs-side change (compose port-mapping edit + redeploy of the Spoolman container) is a **separate** workstream owned operator-/configs-side; it is NOT a 3d-portal commit. Until that compose edit lands, is redeployed on `.190`, and `docker inspect` shows `HostIp: "192.168.2.190"` (not `0.0.0.0` / `::`), this precondition stays open and Story 31.1 stays in `review`.

If the verification fails (Spoolman remains on the Docker default all-interfaces bind after the redeploy), STOP — escalate to operator before merging Story 31.1. Possible resolutions: (a) configs-side fix-up tightening the bind to `192.168.2.190:7912:8000`; (b) accept the all-interfaces exposure as a deliberate operator decision and document the rationale in `docs/operations.md`. Option (a) is the operator's stated preference per the 2026-05-29 decision.

**Verification status (2026-05-29):** Configs-repo + runtime-compose recipe edited to bind Spoolman to `192.168.2.190:7912:8000`; runtime container redeployed on `.190`. Operator-side `docker inspect spoolman --format '{{json .NetworkSettings.Ports}}'` now returns `{"8000/tcp":[{"HostIp":"192.168.2.190","HostPort":"7912"}]}` (explicit LAN-interface-only bind — AC-11 acceptable posture). API smoke from `.190` to `http://192.168.2.190:7912/api/v1/spool` returned HTTP 200 with 9 spools; `http://127.0.0.1:7912/` correctly refused (confirms no loopback exposure). Remote `kattegat` live smoke `SPOOLMAN_LIVE_TEST=1 SPOOLMAN_URL=http://192.168.2.190:7912 apps/api/.venv/bin/pytest tests/test_spools.py::test_spoolman_live_smoke_contract -q` → **1 passed**. AC-11 OD8 close-out precondition is **satisfied** (LAN-only, not all-interfaces). The merging commit (T11.3) still owes the verbatim `OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)` trailer per T8.2; status stays `review` until that commit lands.

The configs-side compose change attaching Spoolman to `portal-network` for Decision AE P4b is a separate precondition: if it has not yet shipped when Story 31.1 enters dev, the story falls back to Decision AE P4a (operator sets `SPOOLMAN_URL=http://localhost:7912` in `.env`; portal-api on docker host network). Both branches use the same env slot — no code change needed to switch.

### AC-12 — `_PUBLIC_ROUTES` allowlist + NFR10 credentialless contract UNTOUCHED

Story 31.1 mounts **no** new routes (Story 31.2 owns route mounting). Therefore:

- `apps/api/app/main.py:_PUBLIC_ROUTES` MUST stay byte-identical to its pre-Story-31.1 state. Grep invariant: `git diff main -- apps/api/app/main.py` shows zero changes to the `_PUBLIC_ROUTES` tuple body.
- `apps/api/app/modules/share/router.py` MUST stay byte-identical to its pre-Story-31.1 state. NFR10 credentialless contract preserved.
- `apps/api/tests/test_route_enforcement_gate.py` MUST continue to pass without modification — the gate test reads `app.routes` and Story 31.1 adds none.

### AC-13 — Determinism gate (NFR19-DETERMINISM-1)

After this story lands, three consecutive `pytest apps/api/tests/ -v` runs return identical pass counts (no flakes introduced). The arq cron task is idempotent by construction (SETNX lock + AC-9 + entirely Redis-driven, no shared in-process state). Coverage: T7.1 below.

## Tasks / Subtasks

- [x] **T1** (AC-1) — Create the `apps/api/app/modules/spools/` package skeleton
  - [x] T1.1 `mkdir apps/api/app/modules/spools/`; add empty `__init__.py`.
  - [x] T1.2 Stub `client.py`, `service.py`, `models.py` with module docstrings citing Decision AD + AE + AF and the Story 31.1 spec path.

- [x] **T2** (AC-2) — Add `spoolman_url` + `spoolman_auth_token` to `Settings`
  - [x] T2.1 In `apps/api/app/core/config.py`, append two fields under a new `# Initiative 19 Story 31.1 (Decision AE) — Spoolman integration` comment block, after the `password_reset_ttl_seconds` field at line ~93. Defaults per AC-2 table.
  - [x] T2.2 In `apps/api/tests/test_config.py` (existing file), append two cases: `test_spoolman_url_defaults_to_internal_docker_hostname` (asserts default `"http://spoolman:8000"`) + `test_spoolman_auth_token_defaults_to_empty_string` (asserts default `""`).
  - [x] T2.3 In `infra/env.example`, append a block:
    ```
    # Initiative 19 Story 31.1 (Decision AE) — Spoolman read-only inventory mirror.
    # Primary topology P4b: portal-api joins the same docker network as Spoolman
    # and resolves http://spoolman:8000. Fallback P4a (transitional, one-line):
    # set SPOOLMAN_URL=http://localhost:7912 if the configs-side compose PR
    # attaching Spoolman to portal-network has not yet shipped. The configs-side
    # Spoolman compose MUST bind to a non-routable host interface (NOT 0.0.0.0
    # exposed via router) — verified separately per OD8.
    # SPOOLMAN_URL=http://spoolman:8000
    # SPOOLMAN_AUTH_TOKEN=
    ```

- [x] **T3** (AC-5) — Define internal Pydantic models in `models.py`
  - [x] T3.1 Implement `SpoolmanFilament`, `SpoolmanSpool`, `SpoolmanVendor`, `SpoolmanSnapshot` per the AC-5 field list. All four classes set `model_config = ConfigDict(extra="ignore")`.
  - [x] T3.2 Add module docstring: `"""Initiative 19 Story 31.1 (Decision AF) — internal Pydantic mirror of Spoolman's response shape. Carries ALL cost-relevant fields end-to-end so Story 31.2's public DTOs + future Phase D cost-calc UX land without a portal-side schema backfill."""`
  - [x] T3.3 Verify `model_dump_json()` + `model_validate_json()` roundtrip is lossless via a quick unit test in T6 (TEST-5 covers this implicitly via the cache write/read path).

- [x] **T4** (AC-3, AC-6, AC-7) — Implement `SpoolmanClient` with timeout + auth + observability
  - [x] T4.1 `class SpoolmanClient` constructor: `SpoolmanClient(*, base_url: str, auth_token: str)`. Construct `httpx.AsyncClient(timeout=httpx.Timeout(5.0))` — single shared async client lifecycle managed by the caller (`async with SpoolmanClient(...) as client:` semantics via `__aenter__` / `__aexit__` delegating to the underlying httpx client). Inline contract comment on the `5.0` per AC-7.
  - [x] T4.2 Three async methods (`list_spools`, `list_filaments`, `list_vendors`) sharing a private `_get(endpoint: str, response_model: type) -> list[T]` helper. The helper:
    - Builds headers `{"Authorization": f"Bearer {self._auth_token}"}` ONLY when `self._auth_token != ""` (AC-3).
    - Wraps the call in `tracer.start_as_current_span(f"spoolman.client.{method}_{endpoint}")` (AC-6).
    - Records `start = time.monotonic()`; calls `await self._client.get(f"{self._base_url}{endpoint}", headers=headers)`; computes `duration_ms = int((time.monotonic() - start) * 1000)`.
    - On success: parses `response.json()` as `list[response_model]` via `TypeAdapter(list[response_model]).validate_python(...)`; logs `spools.client.call` with `extra={...}` per AC-6; emits Sentry breadcrumb level `info`; updates circuit-breaker state to `consecutive_failures = 0`; returns the parsed list.
    - On `httpx.RequestError` / `httpx.HTTPStatusError` (or any exception): logs `spools.client.error` at `WARNING` with `extra["labels.error_class"]`; sets span status to ERROR; emits Sentry breadcrumb level `warning`; increments `consecutive_failures`; if `consecutive_failures >= 3` sets `circuit_open_until = time.monotonic() + 30.0` (inline contract comment per AC-7); re-raises.
    - Before any HTTP attempt, checks `if time.monotonic() < self._circuit_open_until: raise SpoolmanCircuitOpenError()`. New exception class lives in `client.py`.
  - [x] T4.3 Add `SpoolmanCircuitOpenError(Exception)` class — caught by `SpoolsService.refresh_summary()` and treated as a normal client failure (returns `None`, leaves cache untouched).

- [x] **T5** (AC-4, AC-9) — Implement `SpoolsService` cache topology
  - [x] T5.1 `class SpoolsService` constructor: `SpoolsService(*, redis_factory: RedisFactory, client: SpoolmanClient)`. Constants module-level:
    ```python
    # Initiative 19 Story 31.1 (Decision AD) — contract surface; change requires SCP per AC-4.
    _CACHE_KEY = "spools:summary:v1"
    _LAST_SUCCESS_KEY = "spools:summary:last-success-ts"
    _LOCK_KEY = "spools:poll-lock"
    # because "30s TTL — upper bound on stale snapshot served from Redis; poll runs every 60s; AC-7"
    _CACHE_TTL_SECONDS = 30
    # because "90s lock expiry covers worst-case ~5s × 3 entity types + serialization headroom; AC-7"
    _LOCK_EXPIRY_SECONDS = 90
    ```
  - [x] T5.2 `async def get_summary(self) -> SpoolmanSnapshot | None`:
    - Read `_CACHE_KEY` from Redis. If present, `return SpoolmanSnapshot.model_validate_json(value)`.
    - On miss, call `return await self.refresh_summary()` once (the refresh handles lock contention internally).
    - If `refresh_summary()` returns `None` (lock-already-held OR client failed with empty cache), re-read `_CACHE_KEY` one more time (another worker may have just populated it during the lock wait); return parsed snapshot or `None`.
  - [x] T5.3 `async def get_last_success_ts(self) -> datetime | None`:
    - Read `_LAST_SUCCESS_KEY` from Redis; if present, `return datetime.fromisoformat(value.decode())`; else `None`.
  - [x] T5.4 `async def refresh_summary(self) -> SpoolmanSnapshot | None`:
    - `lock_acquired = await redis.set(_LOCK_KEY, b"1", nx=True, ex=_LOCK_EXPIRY_SECONDS)`. If not `lock_acquired`, return `None` (AC-9 leader-election).
    - `try:` call `await client.list_spools()` + `list_filaments()` + `list_vendors()` concurrently via `asyncio.gather(...)`. Assemble `SpoolmanSnapshot(spools=..., filaments=..., vendors=..., fetched_at=datetime.now(UTC))`. Encode via `snapshot.model_dump_json()`. Pipeline: `SET _CACHE_KEY snapshot_json EX _CACHE_TTL_SECONDS` + `SET _LAST_SUCCESS_KEY iso_now` (no TTL). Log `spools.poll.refresh` with `extra["labels.lock_acquired"] = True` + `extra["labels.entity_count"] = total_count`. Return `snapshot`.
    - `except (httpx.RequestError, httpx.HTTPStatusError, SpoolmanCircuitOpenError) as exc:` log `spools.poll.error` at WARNING; return `None`. Cache + sibling stay untouched (Decision AD failure semantics).
    - `finally:` delete the lock (best-effort — TTL covers crash). `await redis.delete(_LOCK_KEY)`.
  - [x] T5.5 Inline contract comments on every magic literal per AC-7 table.

- [x] **T6** (AC-8) — Register the arq cron `poll_spoolman_summary` in the api-arq queue
  - [x] T6.1 New file `apps/api/app/workers/spoolman_poll.py`:
    ```python
    """Initiative 19 Story 31.1 (Decision AD) — arq cron task that refreshes
    the Spoolman snapshot every 60s. Single-poller leader-election via the
    SETNX lock in SpoolsService.refresh_summary(); safe to run on multiple
    api-arq replicas."""
    import logging
    from app.core.config import get_settings
    from app.core.redis import RedisFactory
    from app.modules.spools.client import SpoolmanClient
    from app.modules.spools.service import SpoolsService

    _LOG = logging.getLogger(__name__)


    async def poll_spoolman_summary(_ctx: dict) -> int:
        settings = get_settings()
        redis_factory = RedisFactory(url=settings.redis_url)
        try:
            async with SpoolmanClient(
                base_url=settings.spoolman_url,
                auth_token=settings.spoolman_auth_token,
            ) as client:
                service = SpoolsService(redis_factory=redis_factory, client=client)
                snapshot = await service.refresh_summary()
            return 1 if snapshot is not None else 0
        finally:
            await redis_factory.aclose()
    ```
  - [x] T6.2 Amend `apps/api/app/workers/__init__.py`:
    - Import: `from app.workers.spoolman_poll import poll_spoolman_summary`.
    - `functions` list: append `poll_spoolman_summary`.
    - `cron_jobs` list: append `cron(poll_spoolman_summary, second={0})  # because "FR19-CACHE-1 60s freshness budget; AC-7"`.

- [x] **T7** (AC-10) — Pytest coverage in `apps/api/tests/test_spools.py`
  - [x] T7.1 Create the file; import `pytest`, `pytest_asyncio`, `httpx`, `fakeredis.aioredis`, the in-tree module classes, plus the existing `freezegun` / `monkeypatch` helpers if needed.
  - [x] T7.2 Add fixture `spoolman_settings_overrides` that monkeypatches the cached `Settings` via `get_settings.cache_clear()` + env vars `SPOOLMAN_URL` / `SPOOLMAN_AUTH_TOKEN`.
  - [x] T7.3 Add fixture `mock_spoolman_client` that returns a `SpoolmanClient` with `httpx.MockTransport` injected via `httpx.AsyncClient(transport=httpx.MockTransport(handler))`. Two helper variants: `make_happy_handler(spools=..., filaments=..., vendors=...)` and `make_error_handler(exc=httpx.ConnectError)`.
  - [x] T7.4 Implement TEST-1 through TEST-11 verbatim per AC-10.
  - [x] T7.5 Implement TEST-LIVE-1 with `@pytest.mark.skipif(os.environ.get("SPOOLMAN_LIVE_TEST") != "1", reason="live Spoolman not reachable; opt in via SPOOLMAN_LIVE_TEST=1")`.
  - [x] T7.6 Determinism gate (AC-13): after `pytest apps/api/tests/test_spools.py -v` returns green once, the dev-story execution runs the full suite three times back-to-back via `for i in 1 2 3; do uv run --project apps/api pytest apps/api/tests/ -q; done`; assert identical pass counts. Documented in the Dev Agent Record.

- [ ] **T8** (AC-11) — OD8 close-out gating *(pre-merge operator gate; not a code blocker)*
  - [x] T8.1 Before opening the dev branch's PR / fast-forward merge, the configs-side compose change (`HostIp: "192.168.2.190"` on `8000/tcp` mapped to `HostPort: "7912"`) lands, the Spoolman container is redeployed on `.190`, and the operator runs `docker inspect spoolman --format '{{json .NetworkSettings.Ports}}' | jq` to confirm the bind shows `HostIp: "192.168.2.190"` (NOT `0.0.0.0` / `::`). The configs-side edit + redeploy is a separate workstream owned operator-/configs-side; this story does NOT carry that commit. **Verified 2026-05-29:** configs-repo + runtime compose recipe edited to `192.168.2.190:7912:8000`; runtime redeployed on `.190`; `docker inspect spoolman --format '{{json .NetworkSettings.Ports}}'` returned `{"8000/tcp":[{"HostIp":"192.168.2.190","HostPort":"7912"}]}` (explicit LAN-only bind — AC-11 acceptable posture). Smoke from `.190` to `http://192.168.2.190:7912/api/v1/spool` HTTP 200 with 9 spools; `http://127.0.0.1:7912/` correctly refused (no loopback exposure). Remote `kattegat` live smoke `SPOOLMAN_LIVE_TEST=1 SPOOLMAN_URL=http://192.168.2.190:7912 apps/api/.venv/bin/pytest tests/test_spools.py::test_spoolman_live_smoke_contract -q` → **1 passed**.
  - [x] T8.2 Commit message of the merging commit MUST contain the exact line:
    ```
    OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)
    ```
    (no quotes; one line; verbatim — grep invariant for the close-out audit trail). *Satisfied by commit `b932a9c`: trailer present verbatim at end of commit body — `git log -1 --format=%B b932a9c | grep -F 'OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)'` → 1 match.*
  - [ ] T8.3 If T8.1 fails (`docker inspect` still shows `HostIp: "0.0.0.0"` or `HostIp: "::"` after the redeploy): STOP. Do not merge. Surface to operator with the `docker inspect` output and possible resolutions per AC-11 (preferred: configs-side fix-up tightening the bind to `192.168.2.190:7912:8000`). *(condition did not fire — T8.1 passed; left unchecked since the STOP branch was not taken.)*

- [x] **T9** (AC-12) — Pre-merge grep invariants
  - [x] T9.1 `git diff main -- apps/api/app/main.py` returns zero lines touching `_PUBLIC_ROUTES` (allowlist preservation).
  - [x] T9.2 `git diff main -- apps/api/app/modules/share/router.py` returns zero lines (NFR10 credentialless contract untouched).
  - [x] T9.3 `grep -rnE "current_(user|admin|member_or_admin|admin_or_agent)" apps/api/app/modules/spools/` returns ZERO matches (Story 31.1 mounts no routes; no auth deps).
  - [x] T9.4 `grep -rn "external_service" apps/api/app/modules/spools/client.py` returns ≥ 2 hits (info + warning code paths per AC-6).
  - [x] T9.5 `grep -rn "logger.info" apps/api/app/modules/spools/` — for every hit, the call MUST NOT pass a raw `response.json()` / `response.text` / Pydantic `model_dump()` content; only `entity_count` + label fields per AC-6. (Manually inspect — short module, ≤5 hits expected.)
  - [x] T9.6 `grep -rnE "spools:(summary:v1|summary:last-success-ts|poll-lock)" apps/api/app/modules/spools/service.py` returns exactly 3 hits (one per byte-pinned key per AC-4).
  - [x] T9.7 `grep -nE "second=\{0\}" apps/api/app/workers/__init__.py` returns ≥ 1 hit (the new cron entry per AC-8).

- [x] **T10** (full quality gate) — Pre-merge checks
  - [x] T10.1 `cd /home/ezop/repos/3d-portal && timeout 600 uv run --project apps/api pytest apps/api/tests/ -v` returns green; new pytest count = baseline + 11 (TEST-1..TEST-11) + 2 (T2.2 config tests). Skipped count gains 1 (TEST-LIVE-1).
  - [x] T10.2 `cd /home/ezop/repos/3d-portal/apps/api && uv run ruff format` (auto-fix) + `uv run ruff check` (assert clean).
  - [x] T10.3 `cd /home/ezop/repos/3d-portal && timeout 600 uv run --project workers/render python -c "import sys; sys.path.insert(0, 'apps/api'); from app.workers import WorkerSettings; print(WorkerSettings.functions, WorkerSettings.cron_jobs)"` — sanity: arq worker import path resolves cleanly (catches packaging regressions early). [Optional smoke; passed 2026-05-29: WorkerSettings imports `poll_spoolman_summary`, cron has `second={0}`.]
  - [x] T10.4 No vitest / Playwright / typecheck runs needed (pure backend story). Web checks intentionally skipped per backend-only scope.
  - [x] T10.5 Determinism gate (AC-13) — full backend suite passed three consecutive times after the logging-capture fix: `apps/api/.venv/bin/pytest -q` returned `931 passed, 1 skipped` on each completed run. One combined two-run wrapper hit the 600s command timeout during the second serial run; the third run was re-executed standalone and passed with the same count.

- [x] **T11** (handoff) — Sprint-status + close-out documentation
  - [x] T11.1 Sprint-status flip `31-1-backend-spoolman-client-cache-poll: ready-for-dev → in-progress → review → done`. (bmad-create-story owns `backlog → ready-for-dev`; bmad-dev-story owns `→ in-progress` + `→ review`; codex-review-pass owns `→ done`. Story 31.1 spec authoring step flips backlog → ready-for-dev in the same edit that ships this spec file.)
  - [x] T11.2 Story file Dev Agent Record gets the file list + completion notes per template.
  - [x] T11.3 Commit message scope: `feat(api): Spoolman client + Redis cache + arq poll job (Story 31.1, Init 19)`. Body MUST include the AC-11 OD8 close-out line verbatim per T8.2. *Satisfied by commit `b932a9c` — subject matches verbatim; OD8 trailer present in body (see T8.2).*
  - [x] T11.4 Note in close-out commit body: Story 31.2 depends-on lifts (cache + service + DTOs ready to back `/api/spools/*` routes). *Satisfied by commit `b932a9c` body line: "Story 31.2 can now mount /api/spools/* routes on top of spools:summary:v1 without reaching Spoolman directly from request handlers."*

### Review Findings

Adversarial-review chain across two reviewer rounds against the working tree at commit `b932a9c` and the fix-up `82b4e21`. **Reviewer routing note (deviation from the [[feedback_codex_model_routing]] tag):** the spec routes Story 31.1 to `gpt-5.4-mini` via the native Codex CLI. Direct `codex review --commit b932a9c` attempts were made but the Codex CLI could not access the local working-tree diff reliably (the MCP transport hung mid-call across several retries). Per AGENTS.md § Autonomous development mode, native Codex review is **contractually mandatory only for NFR-prefixed security gates with countersignature requirements** (e.g. Init 5 NFR5-SEC-2). Story 31.1 explicitly disclaims NFR-SECURITY adjacency (see § Story line 14 + § Threat-vector enumeration), so a labeled fallback reviewer is admissible. Fallback used: an independent Hermes `gpt-5.5` delegate reviewer over the same diff range, labeled honestly in this record (no native-Codex impersonation) so the audit trail is unambiguous.

#### Round 7 — `b932a9c` (Hermes gpt-5.5 delegate, fallback)

- **[Important] Spoolman poll lock release is not ownership-safe under TTL-expiry race.** `SpoolsService.refresh_summary` SETNX'd the lock to the constant value `b"1"` and unconditionally `DEL`'d `spools:poll-lock` in `finally`. If a single poll exceeded the 90s `_LOCK_EXPIRY_SECONDS` lease, Redis would expire the lock, a second worker would SETNX a fresh lock, and the first worker's `finally` would then `DEL` the second worker's lock — violating the AC-9 single-poller invariant. → **Patched** in commit `82b4e21`: per-refresh `secrets.token_hex(16)` token; `_release_lock(token)` runs WATCH/MULTI/EXEC compare-and-delete on `_LOCK_KEY` (DEL only when stored value matches our token; foreign value left intact; `WatchError` retries the CAS). Regression test `test_service_refresh_summary_lock_release_is_ownership_safe_under_ttl_expiry_race` hijacks the lock value mid-poll via the `list_spools` side-effect and asserts the foreign token survives the worker's `finally` (verified red against pre-fix code, green after).

#### Round 7b — `82b4e21` (Hermes gpt-5.5 delegate, fallback)

- **Verdict: APPROVED.** No critical / important / minor findings. The CAS-release primitive is the safest shape supported by both production `redis-py 5.3` and the project's `fakeredis 2.35` test harness (no Lua `EVAL` available because `lupa` is not bundled with `fakeredis`); rationale documented inline beside the `finally` branch per the AC-7 magic-constant / contract-pointer discipline.

#### Gates re-run after `82b4e21`

- `apps/api/.venv/bin/ruff format --check .` → PASS.
- `apps/api/.venv/bin/ruff check .` → PASS.
- `apps/api/.venv/bin/pytest tests/test_spools.py -q` → **18 passed, 1 skipped** (TEST-LIVE-1 env-gated).
- `SPOOLMAN_LIVE_TEST=1 SPOOLMAN_URL=http://192.168.2.190:7912 apps/api/.venv/bin/pytest tests/test_spools.py -q` → **19 passed** (live smoke against real Spoolman 0.23.1 at `.190`).
- `apps/api/.venv/bin/pytest -q` → **938 passed, 1 skipped, 1453 warnings** (project-wide non-blocking baseline; Story 31.1 introduces zero new warnings).
- AC-12 grep invariants re-confirmed: zero diff on `apps/api/app/main.py:_PUBLIC_ROUTES`; zero diff on `apps/api/app/modules/share/router.py`.

#### Triage summary

- `decision-needed`: 0.
- `patch`: 1 (Round-7 lock-ownership bug — already applied in `82b4e21`; no outstanding patch work).
- `defer`: 0 (nothing carried to `deferred-work.md` — no deferred items raised in either review round).
- `dismissed`: 0.

All findings resolved on this branch. No HIGH/MEDIUM issues remain. Status flipped `review → done`.

## Dev Notes

### Source-of-truth references

- **PRD:** `_bmad-output/planning-artifacts/prd.md` § Initiative 19 — FR19-LOWSTOCK-1, FR19-SPOOLS-VIEW-1, FR19-CACHE-1, FR19-FAILURE-1, FR19-DATA-CARRY-1 + NFR19-NETWORK-1, NFR19-OBS-1, NFR19-DETERMINISM-1.
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md` § Initiative 19 — Decision AD (cache topology + poll cadence + leader-election + observability), Decision AE (network transport), Decision AF (data-model carry-through). All three decisions land their contracts in Story 31.1's code surface even though only AD + AE are headline-realized here (AF's internal-model carry is shipped by AC-5; the public DTO surface is Story 31.2).
- **Epics:** `_bmad-output/planning-artifacts/epics.md` § Initiative 19 § Story 31.1 — full sketch + pre-enumeration save + test target counts + pre-merge invariants.
- **SCP:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md` § §4.2 + §4.3 + §4.4 (Story 31.1 entry + sprint-status block).
- **Brainstorm:** `_bmad-output/brainstorming/brainstorming-session-2026-05-29-0840.md` (118 ideas; baseline cell + alternative cells; OD1–OD10 register; anti-patterns 7 + 8 + 11 + 14 inform this story).
- **Cross-repo (observability contract):** `~/repos/configs/docs/observability-logging-contract.md` — canonical structured-log field naming (`event.action`, `labels.*`). [NOTE: path referenced by AGENTS.md cross-repo context section; if locally absent during dev, the on-tree precedent at `apps/api/app/core/auth/ratelimit.py:333-352` is the working example to mirror.]
- **Memory entries (mandatory reads before implementation):**
  - `[[feedback_scp_pre_enumeration_phase]]` — existence checklist + cache-coherence-table format + magic-constant contract rule (AC-7 source). Applied in this spec; carry the same discipline into the code-level comments.
  - `[[feedback_codex_model_routing]]` — Story 31.1 routes to `gpt-5.4-mini` per absence of NFR-SECURITY adjacency.
  - `[[feedback_itcm_autonomous_mode]]` — execution mode; the dev-story step does NOT require operator procedural confirmation, only blocks on real blockers (e.g. AC-11 OD8 failure).
  - `[[feedback_pre_merge_gate_checklist]]` — T9 + T10 are the operational gate.
  - `[[feedback_auto_deploy_dev]]` — post-merge auto-deploy to `.190` fires (non-`docs:` / non-`chore:` commit prefix).

### Pre-enumeration save (per [[feedback_scp_pre_enumeration_phase]] § A)

Run 2026-05-29 against pre-Story-31.1 repo state:

1. **Files reused (existing — DO NOT duplicate):**
   - `apps/api/app/core/config.py` — `Settings` Pydantic class. T2 EXTENDS with two new fields; pattern follows the Story 23.3 / Decision Y rate-limit field additions at lines 64-90.
   - `apps/api/app/core/redis.py` — `RedisFactory` class with `.get()` method returning an async `Redis` instance. T5 EXTENDS by constructing fresh factories per arq tick (not via `app.state.redis` — the worker process owns its own factory).
   - `apps/api/app/core/logging.py` — `JsonFormatter` already pass-through-handles `extra={"event.action": ..., "labels.X": ...}` per line 128. T4 + T5 + T6 logs SLOT INTO this convention; no new logging plumbing.
   - `apps/api/app/core/observability.py` — `init_observability()` already wires the OTel tracer provider. T4 obtains a tracer via `opentelemetry.trace.get_tracer(__name__)` and uses `start_as_current_span(...)` directly; no observability-init changes.
   - `apps/api/app/workers/__init__.py` — `WorkerSettings` already establishes the `cron_jobs` + `functions` lists pattern (Init 5 refresh-token cleanup cron at 03:15 UTC). T6 APPENDS one entry to each list. **Critical:** the api-arq queue (`API_QUEUE_NAME = "arq:api"`) is the right one; the render worker (`workers/render/render/worker.py`) MUST NOT be touched.
   - `apps/api/tests/test_config.py` — existing settings tests; T2.2 EXTENDS with two new cases (no new test file for config).
   - `infra/env.example` — existing env-slot documentation; T2.3 EXTENDS with the Initiative 19 block.
2. **Methods extended (existing — DO NOT add parallel implementations):**
   - `Settings` gains exactly 2 fields (`spoolman_url`, `spoolman_auth_token`) — NO new `@field_validator`, NO new property accessor. Plain strings with defaults suffice.
   - `WorkerSettings.functions` + `cron_jobs` each gain 1 entry; no class-attribute reorganization.
3. **New service-layer entry points (NEW — Story 31.1 owns):**
   - `SpoolmanClient.list_spools()` / `list_filaments()` / `list_vendors()` + `_get()` private helper + `SpoolmanCircuitOpenError`.
   - `SpoolsService.get_summary()` / `get_last_success_ts()` / `refresh_summary()`.
   - `poll_spoolman_summary(ctx)` arq task.
4. **Test fixtures (PARTIAL REUSE):**
   - `apps/api/tests/conftest.py` provides `monkeypatch`, `fakeredis` patterns (Init 5 + Init 6 share-router tests). T7.2 + T7.3 ADD two Story-31.1-local fixtures (`spoolman_settings_overrides`, `mock_spoolman_client`) — no edits to the global conftest.
   - The existing `httpx.MockTransport` pattern (used in admin / sot router tests) is the canonical mock approach.
5. **Contracts already enforced (UNTOUCHED by Story 31.1):**
   - NFR10 credentialless contract on `/api/share/<token>/*` (Init 10 Decision N + Init 18 Decision AA). Story 31.1 adds no routes; AC-12 + T9.1 + T9.2 enforce zero touch on `main.py:_PUBLIC_ROUTES` and `share/router.py`.
   - Route enforcement gate (`apps/api/tests/test_route_enforcement_gate.py`). Story 31.1 adds no routes; gate passes unchanged.
   - api-arq queue isolation (Story 13.2 retro lesson — `API_QUEUE_NAME = "arq:api"` separates from render-worker default queue). T6 honors by using `WorkerSettings` (which already sets `queue_name = API_QUEUE_NAME`).
   - JSON structured-log canonical field naming (`event.action` + `labels.*`). T4 + T5 mirror the existing `ratelimit.py:333-352` shape.
6. **Defensive policies adjacent (none reversed):** no Init 19 reversal of prior NFR clauses. Story 31.1 establishes a brand-new outbound-HTTP surface; nothing existing constrains it.

**Net scope after enumeration:** 6 new files (`spools/__init__.py`, `spools/client.py`, `spools/service.py`, `spools/models.py`, `workers/spoolman_poll.py`, `tests/test_spools.py`) + 4 modified files (`core/config.py`, `workers/__init__.py`, `tests/test_config.py`, `infra/env.example`) + 0 alembic migrations + 0 DB schema changes + 0 new dependencies (httpx already in `apps/api/pyproject.toml:23`; opentelemetry, sentry, fakeredis already present).

### Cache-coherence enumeration (per [[feedback_scp_pre_enumeration_phase]] § B)

Story 31.1 owns the **backend Redis cache** side of the topology. The frontend React Query `["spools", "summary"]` cache surface is in Stories 31.3 + 31.4. The architecture.md § Initiative 19 Decision AD cache-coherence table already captures the cross-surface invariants for the FE queryKey; Story 31.1's backend half is single-keyed (`spools:summary:v1` + sibling `last-success-ts` + transient `poll-lock`) with no other backend consumer competing for the keys.

Backend cache-coherence table (Story 31.1 scope):

| Concern | Source: Story 31.1 (this story) | Source: any related backend route/service |
|---|---|---|
| Staleness budget (`spools:summary:v1` TTL) | 30s (Redis TTL); 60s effective via the arq cron's `second={0}` cadence | n/a — single-keyed; Story 31.2 reads via `SpoolsService.get_summary()` only |
| Retry policy | client-side circuit breaker (3 fails → 30s open); no automatic retry within a single `_get()` call | n/a |
| Mutation propagation | n/a — read-only mirror; no portal-side writes to `spools:summary:v1` outside `refresh_summary()` | n/a — Story 31.2's route handlers do NOT call `refresh_summary()` (they only `get_summary()`); the cron owns the write path |
| Cache eviction | natural TTL expiry; manual `DELETE` only on lock-release inside `refresh_summary()`'s `finally` (lock key, NOT the cache key) | n/a |
| Cache seeding | arq cron `poll_spoolman_summary` is the primary seeder; `get_summary()` on cold-cache miss triggers a single live fetch as fallback (warm-start path post-deploy before the first cron tick) | n/a |

Decision rule: only Story 31.1 owns the backend Redis cache for `spools:summary:v1`. No backend route or service competes for these keys → single-author cache topology is the clean shape. No design-choice resolution needed beyond the per-key contract pinning in AC-4.

### Magic-constant contract pointing (per [[feedback_scp_pre_enumeration_phase]] § C)

All six numeric / time constants Story 31.1 introduces appear in the AC-7 table with their contract pointers. The inline code comments on each literal are NOT optional — they are the audit trail for the next round of Codex review and for any future story revisiting this surface (e.g. Phase D cost-calc UX revisiting the cache schema). The pattern to follow verbatim:

```python
# because "Spoolman is LAN-only on .190, typical response ~50ms; 5s upper bound
# flags genuine outage rather than transient latency — Decision AD"
_HTTPX_TIMEOUT_SECONDS = 5.0
```

If a reviewer (human or Codex) finds a magic constant in `apps/api/app/modules/spools/` or `apps/api/app/workers/spoolman_poll.py` without an adjacent contract comment, it is a P1 fix-up. This is the round-1 spec quality gate the SCP pre-enumeration discipline exists to catch.

### Threat-vector enumeration

Story 31.1 routes to `gpt-5.4-mini` per `[[feedback_codex_model_routing]]` — no NFR-SECURITY adjacency. The full per-`feedback_security_vector_enumeration` enumeration table is NOT mandatory for this story. Brief survey of the surface added:

- **Outbound egress to a LAN-only service.** Spoolman is not internet-routable per AC-11 + OD8 close-out. No credential leakage class.
- **Bearer token in `Authorization` header.** Only sent when non-empty; MVP-A default empty. Future P3d Phase C would activate this surface; today it's dormant.
- **No CSRF / cookie / auth-state-consulting surface.** Story 31.1 adds zero HTTP endpoints; auth-state consultation lives in Story 31.2.
- **No PII storage.** Spoolman data is filament inventory (vendor names, color hex, weight grams); not personal data.
- **Redis cache key namespace collision risk.** New keys (`spools:summary:v1` etc.) use the `spools:` prefix; existing portal Redis keys use `share:`, `ratelimit:`, `auth:`, `csrf:`. No collision.

No P1/P2 unmitigated vector identified. Codex `gpt-5.4-mini` routing is appropriate.

### Files this story touches (READ existing state before editing)

| File | Action | Why |
|---|---|---|
| `apps/api/app/modules/spools/__init__.py` | NEW (empty) | T1.1 — module package marker |
| `apps/api/app/modules/spools/client.py` | NEW | T4 — `SpoolmanClient` + `SpoolmanCircuitOpenError` |
| `apps/api/app/modules/spools/service.py` | NEW | T5 — `SpoolsService` + cache topology constants |
| `apps/api/app/modules/spools/models.py` | NEW | T3 — internal Pydantic mirror (Decision AF full surface) |
| `apps/api/app/workers/spoolman_poll.py` | NEW | T6.1 — arq task entry point |
| `apps/api/tests/test_spools.py` | NEW | T7 — 11 pytest cases + 1 env-gated live integration |
| `apps/api/app/core/config.py` | MODIFY (append 2 fields) | T2.1 — `spoolman_url` + `spoolman_auth_token` |
| `apps/api/app/workers/__init__.py` | MODIFY (append 1 cron + 1 function) | T6.2 — cron registration |
| `apps/api/tests/test_config.py` | EXTEND (append 2 cases) | T2.2 — default-values coverage |
| `infra/env.example` | EXTEND (append doc block) | T2.3 — operator-facing env documentation |

**Files this story MUST NOT touch:**

- `apps/api/app/main.py` — no new route mounting in Story 31.1; `_PUBLIC_ROUTES` allowlist preserved (AC-12 + T9.1).
- `apps/api/app/modules/share/router.py` — NFR10 credentialless contract preserved (AC-12 + T9.2).
- `apps/api/app/router.py` — no new module router to include yet (Story 31.2 owns the `include_router(spools_router)` line).
- `workers/render/` — render worker is orthogonal; touching it would re-introduce the Story 13.2 queue-collision bug.
- `apps/web/` — pure backend story; web surface lives in Stories 31.3 + 31.4 + 31.5.
- `~/repos/configs/docker-compose-recipes/spoolman.yml` — out-of-repo per HC2 trip-wire (AGENTS.md § Cross-repo context); the configs-side compose change is a separate PR owned by the operator.

### Implementation skeleton

**`apps/api/app/modules/spools/models.py`:**

```python
"""Initiative 19 Story 31.1 (Decision AF) — internal Pydantic mirror of
Spoolman's response shape. Carries ALL cost-relevant fields end-to-end so
Story 31.2's public DTOs + future Phase D cost-calc UX land without a
portal-side schema backfill. Models tolerate Spoolman schema drift via
extra='ignore'.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SpoolmanVendor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str


class SpoolmanFilament(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str
    vendor_id: int | None = None
    vendor_name: str | None = None
    material: str | None = None
    color_hex: str | None = None
    price: float | None = None
    weight: float | None = None
    spool_weight: float | None = None


class SpoolmanSpool(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    filament_id: int
    price: float | None = None
    remaining_weight: float | None = None
    initial_weight: float | None = None
    used_weight: float | None = None
    spool_weight: float | None = None
    first_used: datetime | None = None
    last_used: datetime | None = None
    archived: bool = False
    lot_nr: str | None = None


class SpoolmanSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    spools: list[SpoolmanSpool]
    filaments: list[SpoolmanFilament]
    vendors: list[SpoolmanVendor]
    fetched_at: datetime
```

**`apps/api/app/modules/spools/client.py` (skeleton — full body in T4):**

```python
"""Initiative 19 Story 31.1 (Decisions AD + AE) — httpx wrapper around
Spoolman's read-only /api/v1/* endpoints. Single-instance circuit breaker
(3 fails -> 30s open). Structured logging + OTel span + Sentry breadcrumb
on every call (NFR19-OBS-1)."""

import logging
import time
from typing import Self, TypeVar

import httpx
import sentry_sdk
from opentelemetry import trace
from pydantic import BaseModel, TypeAdapter

from app.modules.spools.models import SpoolmanFilament, SpoolmanSpool, SpoolmanVendor

_LOG = logging.getLogger(__name__)
_TRACER = trace.get_tracer(__name__)

T = TypeVar("T", bound=BaseModel)


class SpoolmanCircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is open (3 consecutive failures
    within the 30s open window). Caller treats as a normal client failure."""


class SpoolmanClient:
    def __init__(self, *, base_url: str, auth_token: str) -> None:
        # because "Spoolman is LAN-only on .190, typical response ~50ms; 5s upper bound
        # flags genuine outage rather than transient latency — Decision AD, AC-7"
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))
        self._base_url = base_url.rstrip("/")
        self._auth_token = auth_token
        # Circuit breaker state.
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0  # monotonic seconds; open while now < this

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.aclose()

    # --- list_spools / list_filaments / list_vendors share _get(...) ---

    async def list_spools(self) -> list[SpoolmanSpool]:
        return await self._get("/api/v1/spool", SpoolmanSpool)

    async def list_filaments(self) -> list[SpoolmanFilament]:
        return await self._get("/api/v1/filament", SpoolmanFilament)

    async def list_vendors(self) -> list[SpoolmanVendor]:
        return await self._get("/api/v1/vendor", SpoolmanVendor)

    async def _get(self, endpoint: str, response_model: type[T]) -> list[T]:
        # ... timeout guard, circuit-breaker pre-check, span wrap, headers,
        # success/failure log + breadcrumb, circuit-breaker state update.
        # See T4.2 for the full body.
        ...
```

**`apps/api/app/modules/spools/service.py` (skeleton — full body in T5):**

```python
"""Initiative 19 Story 31.1 (Decision AD) — Redis cache topology +
single-poller leader-election around Spoolman snapshots."""

import logging
from datetime import UTC, datetime

import httpx

from app.core.redis import RedisFactory
from app.modules.spools.client import SpoolmanCircuitOpenError, SpoolmanClient
from app.modules.spools.models import SpoolmanSnapshot

_LOG = logging.getLogger(__name__)

# Initiative 19 Story 31.1 (Decision AD) — contract surface; change requires SCP per AC-4.
_CACHE_KEY = "spools:summary:v1"
_LAST_SUCCESS_KEY = "spools:summary:last-success-ts"
_LOCK_KEY = "spools:poll-lock"

# because "30s upper bound on stale snapshot served from Redis; poll runs every 60s
# but a fresh request within the 30-60s gap still serves the slightly-staler cached
# value rather than triggering a synchronous fetch in the request path — AC-7"
_CACHE_TTL_SECONDS = 30

# because "90s comfortably covers stuck-poll scenarios (~5s × 3 entity types +
# serialization headroom) without holding the lock past the next 60s tick — AC-7"
_LOCK_EXPIRY_SECONDS = 90


class SpoolsService:
    def __init__(self, *, redis_factory: RedisFactory, client: SpoolmanClient) -> None:
        self._redis = redis_factory.get()
        self._client = client

    async def get_summary(self) -> SpoolmanSnapshot | None: ...
    async def get_last_success_ts(self) -> datetime | None: ...
    async def refresh_summary(self) -> SpoolmanSnapshot | None: ...
```

### Conventions to follow (recap from project-context.md)

- **Annotated dep pattern:** N/A in Story 31.1 (no FastAPI dependencies introduced; Story 31.2 wires `Depends(...)` for routes).
- **`Session.exec(select(...))`:** N/A in Story 31.1 (no DB access — pure Redis + Spoolman HTTP).
- **Soft-delete filter:** N/A.
- **Logger namespacing:** module-level `_LOG = logging.getLogger(__name__)` per the codebase convention (`apps/api/app/workers/cleanup_refresh_tokens.py:14` is the canonical worker example).
- **Structured-log shape:** `_LOG.info("spools.client.call", extra={"event.action": "spools.client.call", "labels.X": Y, ...})` matching `ratelimit.py:333-352` precedent.
- **ruff E,F,W,I,B,UP,SIM,RUF line-length 100 py312** — run `ruff format` + `ruff check --fix` before commit (T10.2).
- **Type hints:** modern union syntax (`int | None`); `typing.Self` for `__aenter__`; no `Optional[...]` / `Union[...]` imports.
- **i18n:** N/A for Story 31.1 (no user-facing strings; structured logs are operator-facing in en-only).
- **Visual regression:** N/A (pure backend).
- **Commit message:** conventional commits `feat(api): Spoolman client + Redis cache + arq poll job (Story 31.1, Init 19)`. Scope `api` (primary surface). Body MUST include the AC-11 OD8 close-out line verbatim.

### Project Structure Notes

- All file paths align with existing project structure (project-context.md § Module layout; AGENTS.md § Repository layout — `apps/api/app/modules/spools/` is the documented v2 slot).
- New module placement follows the Init 6 invite module precedent (`apps/api/app/modules/invite/` — module-local `models.py` / `service.py` shape).
- New arq task placement follows the Init 5 + Init 8 precedent (`apps/api/app/workers/<task_name>.py` + registration in `apps/api/app/workers/__init__.py`).
- No deviation from project structure; no new directories outside the module + worker conventions.

### References

- [Source: `apps/api/app/workers/__init__.py:30-43`] — `WorkerSettings` class shape: `queue_name`, `functions`, `cron_jobs`, `redis_settings`. T6.2 extends `functions` + `cron_jobs`.
- [Source: `apps/api/app/workers/cleanup_refresh_tokens.py:14-35`] — canonical arq task shape (module-level logger, `extra={"event.action": ..., "labels.X": ...}` structured logging, sync/async split with `_sync` helper if needed). Story 31.1's task is pure-async (no DB session) so no sync split needed.
- [Source: `apps/api/app/core/auth/ratelimit.py:333-352`] — canonical structured-log shape with `event.action` + `labels.scope` + `labels.key` etc. (AC-6 follows this pattern; `labels.external_service` is the new addition).
- [Source: `apps/api/app/core/config.py:64-90`] — Init 16 Story 23.3 pattern for appending env-driven Settings fields with inline contract comments + cross-references to the decision that pinned the literal. T2.1 follows.
- [Source: `apps/api/app/core/redis.py:1-17`] — `RedisFactory(*, url=...)` constructor pattern that the arq task instantiates per tick.
- [Source: `apps/api/app/core/observability.py:14-49`] — `init_observability()` already wires the OTel tracer provider; `trace.get_tracer(__name__).start_as_current_span(...)` is directly usable in `client.py`.
- [Source: `apps/api/app/core/logging.py:128`] — `JsonFormatter` pass-through-handles `extra={"event.action": ..., "labels.X": ...}` — no formatter changes needed.
- [Source: `apps/api/pyproject.toml:23`] — `httpx>=0.28` already a dependency; no new entry needed.
- [Source: `apps/api/app/main.py:50-61`] — `_PUBLIC_ROUTES` allowlist (AC-12: this story does NOT touch it).
- [Source: `apps/api/app/modules/share/router.py`] — NFR10 credentialless surface (AC-12: byte-identical to pre-Story-31.1 state).
- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 19 Decisions AD + AE + AF] — primary design rationale (cache topology + transport + carry-through).
- [Source: `_bmad-output/planning-artifacts/prd.md` § Initiative 19 FR19-* + NFR19-*] — Functional + non-functional requirements.
- [Source: `_bmad-output/planning-artifacts/epics.md` § Initiative 19 Story 31.1] — story-level scope + pre-merge invariants (the in-spec list extends these with byte-pin language).
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md` § §4.4] — sprint-status block; AC-11 lifts the OD8 precondition language verbatim.
- [Source: `~/.claude/projects/-home-ezop-repos-3d-portal/memory/feedback_scp_pre_enumeration_phase.md`] — pre-enumeration discipline + cache-coherence table format + magic-constant contract rule.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context) via bmad-dev-story skill — Story 31.1 execution.

### Debug Log References

Pre-merge verification runs on branch `feat/E31.1-backend-spoolman-client-cache-poll` against the post-live-smoke working tree (round-6 fix-up — nested vendor/filament shape):

- `apps/api/.venv/bin/ruff format --check apps/api` → PASS (no reformatting needed).
- `apps/api/.venv/bin/ruff check apps/api` → PASS (clean; AC-12 grep invariants re-validated after the nested-shape fix-up).
- `apps/api/.venv/bin/pytest tests/test_spools.py -q` → **17 passed, 1 skipped** (TEST-LIVE-1 skipped via the `SPOOLMAN_LIVE_TEST=1` env gate as designed; one additional regression case pinned the nested vendor/filament response shape uncovered by the live smoke).
- Env-gated live integration: `SPOOLMAN_LIVE_TEST=1 SPOOLMAN_URL=http://192.168.2.190:7912 apps/api/.venv/bin/pytest tests/test_spools.py::test_spoolman_live_smoke_contract -q` → **1 passed** (contract pinned against the real Spoolman 0.23.1 response shape on `.190`; nested `vendor`/`filament` object payloads parse losslessly through the internal Pydantic models after the fix-up).
- Full backend suite `apps/api/.venv/bin/pytest -q` → **937 passed, 1 skipped, 1453 warnings in 303.09s**. The warning bucket remains the existing project-wide non-blocking noise (deprecation / Pydantic compat / SQLAlchemy decl-base) — Story 31.1 introduces none of its own.
- Codex adversarial review — Rounds 1–5 verdict **APPROVE, no blocking findings**. The Codex live-shape follow-up review (post-live-smoke) confirmed **no new code-level blocking issue** introduced by the nested-shape fix-up; the review chain stays closed on the code side.

### Completion Notes List

- AC-1..AC-10 + AC-12 + AC-13 remain realized on this branch after the Round 1–5 review chain and the round-6 live-smoke fix-up. Cache topology contract (AC-4 byte-pinned keys), magic-constant contract comments (AC-7), observability labels (AC-6), SETNX leader-election (AC-9), and the 60s cron cadence (AC-8) are in place and exercised by `tests/test_spools.py`.
- `SpoolmanClient._get` short-circuits via `SpoolmanCircuitOpenError` once `_CIRCUIT_FAILURE_THRESHOLD` (3) consecutive failures land within the `_CIRCUIT_OPEN_SECONDS` (30) window; `SpoolsService.refresh_summary` catches it alongside `httpx.RequestError` / `httpx.HTTPStatusError` and returns `None` without touching the cache or sibling timestamp (Decision AD failure semantics).
- Review-round follow-ups extended `tests/test_spools.py` with five Codex-driven cases beyond the original TEST-1..TEST-11 set: schema-drift safety on cold-cache miss, cold-cache lock-contention leader-wait, lock-release-race retry of the live fetch, sibling-call draining before lock release, and the `labels.lock_acquired` label assertion on the refresh-path client log.
- **Live-smoke round-6 fix-up (nested vendor/filament response shape).** The env-gated `test_spoolman_live_smoke_contract` against the real Spoolman 0.23.1 instance at `http://192.168.2.190:7912` surfaced that `/api/v1/spool` returns `filament` as a nested object (containing the filament fields **plus** a nested `vendor` object) rather than the flat `filament_id` / `vendor_id` projection assumed by the original mocks, and `/api/v1/filament` returns `vendor` as a nested object rather than flat `vendor_id` / `vendor_name`. `apps/api/app/modules/spools/models.py` was extended so `SpoolmanSpool` / `SpoolmanFilament` parse the nested objects losslessly while still exposing the flat id/name accessors downstream consumers (Story 31.2 DTOs) depend on — `extra="ignore"` left intact for forward-compat with 0.24.x drift. One additional regression case was added to `tests/test_spools.py` to pin the nested-shape contract under mocked transport so the suite catches schema drift without requiring the live smoke. Total spool-suite count is now 17 passing + 1 skipped (TEST-LIVE-1 env-gated).
- **Codex live-shape follow-up review verdict: no new code-level blocking issue.** The adversarial review of the nested-shape fix-up confirmed the response-shape change is correctly absorbed inside the internal Pydantic mirror without leaking schema concerns to the cache or service layer; magic-constant contract comments and AC-4 byte-pinned keys remain untouched; AC-12 grep invariants re-validated clean. The code-side review chain is closed.
- **AC-11 / OD8 pre-merge precondition — verification PASSES (LAN-only bind confirmed 2026-05-29).** Operator-side configs-repo + runtime-compose recipe edited to bind Spoolman to `192.168.2.190:7912:8000`; runtime container redeployed on `.190`. `docker inspect spoolman --format '{{json .NetworkSettings.Ports}}'` now returns `{"8000/tcp":[{"HostIp":"192.168.2.190","HostPort":"7912"}]}` — explicit LAN-interface-only bind, matching AC-11's acceptable posture (NOT the rejected `0.0.0.0` / `::` all-interfaces exposure). Operator decision (2026-05-29): Spoolman MUST remain reachable from the LAN because the printer pushes filament-usage updates live and the operator + phone consume Spoolman on the LAN; the target posture is therefore `HostIp: "192.168.2.190"` (explicit LAN-only bind), NOT `127.0.0.1`-only. Smoke evidence: API call from `.190` to `http://192.168.2.190:7912/api/v1/spool` returned HTTP 200 with 9 spools; `http://127.0.0.1:7912/` correctly refused (no loopback exposure); remote `kattegat` env-gated live smoke `SPOOLMAN_LIVE_TEST=1 SPOOLMAN_URL=http://192.168.2.190:7912 apps/api/.venv/bin/pytest tests/test_spools.py::test_spoolman_live_smoke_contract -q` → **1 passed**. T8.1 is therefore checked; T8.3 STOP condition did not fire. **T8.2 + T11.3 + T11.4 remain pending** — the merging commit MUST still carry the verbatim trailer `OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)` per AC-11. The configs-side compose edit + redeploy is owned operator-/configs-side and is NOT a 3d-portal commit. Status stays **review** until the 3d-portal merging commit lands with the OD8 trailer.
- T10.3 (cross-project arq worker import smoke) is marked optional in the spec and was not re-executed for the live-shape fix-up; T9.1/T9.2 grep invariants stay confirmed (zero diff on `apps/api/app/main.py:_PUBLIC_ROUTES` and `apps/api/app/modules/share/router.py`).
- `RedisFactory(client=fake)` constructor path is exercised by the `fake_redis_factory` pytest fixture; no source change required in `app/core/redis.py`.
- Status stays **review** — code-side gates and the adversarial-review chain (incl. live-shape follow-up) are complete, and the AC-11 OD8 configs-side bind precondition is now verified LAN-only. Merge gate remaining: the 3d-portal commit landing the existing code changes with the verbatim `OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)` trailer (T8.2 / T11.3 / T11.4).
- **Round-7 fix-up (lock-ownership invariant under TTL-expiry race).** Adversarial review of commit `b932a9c` flagged a real ownership bug in `SpoolsService.refresh_summary`: the lock was SETNX'd to the constant value `b"1"` and the `finally` branch ran an unconditional `DEL` on `spools:poll-lock`. If a single poll exceeded the 90s `_LOCK_EXPIRY_SECONDS` lease, Redis would expire the lock, a second worker would SETNX a fresh lock of its own, and the first worker's `finally` would then `DEL` the second worker's lock — violating the AC-9 single-poller invariant and opening a third-worker contention window. Fix: each `refresh_summary` invocation now generates a 16-byte hex token via `secrets.token_hex(16)`, SETNX'es the lock to that token, and releases via a private `_release_lock(token)` helper that performs a WATCH/MULTI/EXEC compare-and-delete on `_LOCK_KEY` (DEL only when the stored value still matches our token; foreign value left intact; `WatchError` retries the CAS). Lua `EVAL` would be a one-call equivalent but the project's `fakeredis` test harness lacks the optional `lupa` Lua runtime, so transactions were picked as the safest primitive supported by both production `redis-py 5.3` and `fakeredis.aioredis 2.35` without an extra dependency — rationale documented inline beside the `finally` branch (AC-7 magic-constant / contract-pointer discipline preserved). One new regression case `test_service_refresh_summary_lock_release_is_ownership_safe_under_ttl_expiry_race` in `tests/test_spools.py` hijacks the lock value mid-poll via the `list_spools` side-effect and asserts the foreign token survives the worker's `finally`; verified red against pre-fix code, green after the fix. Total spool-suite count is now **18 passing + 1 skipped** (TEST-LIVE-1 env-gated). Gates rerun: `ruff format --check apps/api`, `ruff check apps/api`, targeted `apps/api/.venv/bin/pytest apps/api/tests/test_spools.py -q`, full backend `apps/api/.venv/bin/pytest -q`. Status stays **review** — merging commit gate (T8.2 / T11.3 / T11.4) unchanged.

### File List

New (6):

- `apps/api/app/modules/spools/__init__.py` — package marker + module docstring (no exports yet; routes land in Story 31.2).
- `apps/api/app/modules/spools/client.py` — `SpoolmanClient` (httpx wrapper + circuit breaker + structured-log/OTel/Sentry observability) and `SpoolmanCircuitOpenError`.
- `apps/api/app/modules/spools/service.py` — `SpoolsService` with `get_summary` / `get_last_success_ts` / `refresh_summary`; module-level cache-topology constants for the byte-pinned Redis keys + TTL + lock expiry.
- `apps/api/app/modules/spools/models.py` — `SpoolmanVendor`, `SpoolmanFilament`, `SpoolmanSpool`, `SpoolmanSnapshot` (all `extra="ignore"`); round-6 live-smoke fix-up extended `SpoolmanSpool` / `SpoolmanFilament` to parse the nested `filament` / `vendor` objects returned by Spoolman 0.23.1 while preserving the flat id/name accessors Story 31.2 DTOs depend on.
- `apps/api/app/workers/spoolman_poll.py` — `poll_spoolman_summary(_ctx)` arq task constructing a fresh `RedisFactory` + `SpoolmanClient` per tick.
- `apps/api/tests/test_spools.py` — TEST-1..TEST-11 unit suite + 5 review-round follow-up cases (schema-drift, cold-cache lock-contention, lock-release race, sibling-call drain, refresh-path lock label) + 1 live-shape regression case pinning the nested vendor/filament response shape under mocked transport (round-6 follow-up) + TEST-LIVE-1 env-gated integration. A local `_CaptureHandler` helper is attached to the module logger so AC-6 log assertions survive `configure_logging()` resets.

Modified (4):

- `apps/api/app/core/config.py` — appended `spoolman_url` and `spoolman_auth_token` fields under an Initiative 19 / Decision AE comment block (after `password_reset_ttl_seconds`).
- `apps/api/app/workers/__init__.py` — imported `poll_spoolman_summary`; appended it to `WorkerSettings.functions`; appended `cron(poll_spoolman_summary, second={0})` to `WorkerSettings.cron_jobs` with the AC-7 contract comment.
- `apps/api/tests/test_config.py` — two new cases covering the default values of `spoolman_url` and `spoolman_auth_token`.
- `infra/env.example` — appended the Initiative 19 / Decision AE env-slot documentation block (`SPOOLMAN_URL`, `SPOOLMAN_AUTH_TOKEN`, P4a fallback note, OD8 bind precondition reference).

## Change Log

| Date | Author | Note |
|---|---|---|
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | Initial implementation landed on `feat/E31.1-backend-spoolman-client-cache-poll`. Backend Spoolman client + Redis cache + arq 60s poll + env config per AC-1..AC-10 + AC-12 + AC-13. Ruff format/check clean; `tests/test_spools.py` 11/1 (passed/skipped); full backend suite 931/1 stable across three runs (AC-13 determinism gate). AC-11 OD8 configs-side bind verification remains a pre-merge operator gate. Status flipped `ready-for-dev → review`. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | Codex adversarial review Rounds 1–4 fix-ups absorbed on the same branch: extended `tests/test_spools.py` with five additional invariants (schema-drift safety on cold-cache miss, cold-cache lock-contention leader-wait, lock-release-race retry, sibling-call drain before lock release, refresh-path `labels.lock_acquired` assertion). Magic-constant contract comments and observability label coverage tightened to match. Status stays `review`. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | Codex adversarial review Round 5 verdict **APPROVE — no blocking findings**. Verified gates post-Round-5: `ruff format --check apps/api` PASS, `ruff check apps/api` PASS, `apps/api/.venv/bin/pytest tests/test_spools.py -q` 16 passed / 1 skipped, full backend suite `apps/api/.venv/bin/pytest -q` 936 passed / 1 skipped / 1453 warnings in 300.19s (project-wide non-blocking warning baseline; Story 31.1 introduces none). Review chain closed. Status stays `review` until operator OD8 close-out (T8) and the merging commit (T11.3/T11.4) land. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | Round-6 fix-up — live Spoolman smoke against `http://192.168.2.190:7912` discovered Spoolman 0.23.1 returns nested `filament` / `vendor` objects on `/api/v1/spool` and `/api/v1/filament` (not the flat `filament_id` / `vendor_id` / `vendor_name` projection the original mocks assumed). `apps/api/app/modules/spools/models.py` extended to parse the nested shape losslessly while preserving the flat id/name accessors Story 31.2 DTOs depend on; one regression test added to `tests/test_spools.py` pinning the shape under mocked transport. Verified gates: `ruff format --check apps/api` PASS, `ruff check apps/api` PASS, `apps/api/.venv/bin/pytest tests/test_spools.py -q` **17 passed / 1 skipped**, env-gated `SPOOLMAN_LIVE_TEST=1 SPOOLMAN_URL=http://192.168.2.190:7912 pytest tests/test_spools.py::test_spoolman_live_smoke_contract -q` **1 passed**, full backend suite `apps/api/.venv/bin/pytest -q` **937 passed / 1 skipped / 1453 warnings in 303.09s**. Codex live-shape follow-up review verdict: **no new code-level blocking issue**. Status stays `review`. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | **AC-11 / OD8 pre-merge BLOCKER recorded.** Configs-side verification on `.190` currently FAILS: `docker inspect spoolman --format '{{json .NetworkSettings.Ports}}'` reports `HostIp: "0.0.0.0"` and `HostIp: "::"` bound to `HostPort: "7912"` (Spoolman exposed on all host interfaces, not the non-routable bind required by AC-11). Per AC-11 this is the explicit STOP condition — do NOT mark Story 31.1 done, do NOT claim OD8 close-out, do NOT treat this branch as merge-ready. Resolution owned operator-/configs-side (tighten the bind to `127.0.0.1:7912`, OR record deliberate-exposure rationale in `docs/operations.md` per AC-11 (b)). Code-side gates and the adversarial-review chain (incl. live-shape follow-up) remain green; the blocker is purely the configs-side bind. Status stays `review`; T8.1/T8.2/T8.3 + T11.3/T11.4 stay unchecked until the bind is verified non-routable. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | **AC-11 / T8 / Completion Notes wording clarified per operator decision (record-keeping only — no code change).** Operator confirmed Spoolman MUST remain reachable from the LAN because the printer pushes filament-usage updates live and the operator + phone consume Spoolman on the LAN; a strict `127.0.0.1`-only bind is therefore NOT the target. AC-11 + T8.1/T8.2/T8.3 + the AC-11 Completion-Notes blocker entry rewritten to reflect the actual gate: reject the Docker default all-interfaces exposure (`HostIp: "0.0.0.0"` / `HostIp: "::"`), accept the explicit LAN-interface-only bind (`HostIp: "192.168.2.190"` on `8000/tcp` mapped to `HostPort: "7912"`). T8.2 commit-trailer string updated to `OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)`. The configs-side compose edit + redeploy is explicitly flagged as a separate operator-/configs-side workstream (NOT a 3d-portal commit) that requires `docker inspect` to show `HostIp: "192.168.2.190"` (not `0.0.0.0` / `::`) before this story can leave `review`. No code changed in this update; status stays `review`. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | **AC-11 / OD8 close-out — configs-side LAN-only bind verified (record-keeping only — no code change).** Operator-side configs-repo + runtime-compose recipe edited to `192.168.2.190:7912:8000`; runtime container redeployed on `.190`. `docker inspect spoolman --format '{{json .NetworkSettings.Ports}}'` returned `{"8000/tcp":[{"HostIp":"192.168.2.190","HostPort":"7912"}]}` (explicit LAN-only bind — AC-11 acceptable posture, NOT the rejected all-interfaces exposure). API smoke from `.190` to `http://192.168.2.190:7912/api/v1/spool` HTTP 200 with 9 spools; `http://127.0.0.1:7912/` correctly refused (no loopback exposure). Remote `kattegat` env-gated live smoke `SPOOLMAN_LIVE_TEST=1 SPOOLMAN_URL=http://192.168.2.190:7912 apps/api/.venv/bin/pytest tests/test_spools.py::test_spoolman_live_smoke_contract -q` → **1 passed** (contract pinning against real Spoolman 0.23.1 at the LAN bind). AC-11 narrative gains a "Verification status" paragraph; T8.1 checked with the verification evidence inline; T8.3 STOP condition did not fire (left unchecked since the failure branch was not taken); the AC-11 Completion-Notes blocker entry rewritten as a precondition-PASSES note. T8.2 (commit trailer `OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)`) and T11.3 / T11.4 (the merging commit body) remain pending — status stays **review** until the 3d-portal commit lands with the verbatim trailer. No code changed in this update. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | **Round-7 fix-up — lock-ownership invariant under TTL-expiry race.** Adversarial review of commit `b932a9c` flagged a real bug in `SpoolsService.refresh_summary`: SETNX wrote the constant value `b"1"` and `finally` ran an unconditional `DEL` on `spools:poll-lock`. If a poll exceeded the 90s lease, Redis would expire the lock, a second worker would SETNX a fresh lock, and the first worker's `finally` would then `DEL` the second worker's lock — violating the AC-9 single-poller invariant. Fix: each `refresh_summary` invocation generates a 16-byte hex token via `secrets.token_hex(16)`, SETNX'es the lock to that token, and releases via a private `_release_lock(token)` helper that runs a WATCH/MULTI/EXEC compare-and-delete on `_LOCK_KEY` (DEL only when stored value still matches our token; foreign value left intact; `WatchError` retries the CAS). Lua `EVAL` was considered first per project guidance but the project's `fakeredis 2.35` test harness lacks the optional `lupa` Lua runtime, so transactions were chosen as the safest primitive supported by both production `redis-py 5.3` and `fakeredis.aioredis` without an extra dependency — rationale documented inline beside the `finally` branch (AC-7 contract-pointer discipline preserved). New regression test `test_service_refresh_summary_lock_release_is_ownership_safe_under_ttl_expiry_race` hijacks the lock value mid-poll via the `list_spools` side-effect and asserts the foreign token survives the worker's `finally`; verified red against pre-fix code, green after the fix. Gates rerun: `apps/api/.venv/bin/ruff format --check .` PASS (195 files), `apps/api/.venv/bin/ruff check .` PASS (clean), targeted `apps/api/.venv/bin/pytest tests/test_spools.py -q` → **18 passed / 1 skipped** (three consecutive runs, AC-13 determinism stable), full backend suite `apps/api/.venv/bin/pytest -q` → **938 passed / 1 skipped / 1453 warnings in 303.33s** (Story 31.1 introduces zero new warnings; +1 case vs. previous 937 reflects the new ownership-race regression). Status stays **review** — merging commit gate (T8.2 / T11.3 / T11.4) unchanged. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-code-review | **Code-review close-out — status flipped `review → done` (record-keeping only — no code change).** Adversarial-review chain across two reviewer rounds against `b932a9c` + fix-up `82b4e21`. Native Codex CLI (spec-tagged `gpt-5.4-mini` per `[[feedback_codex_model_routing]]`) hung on MCP transport when attempting `codex review --commit b932a9c`; per AGENTS.md § Autonomous development mode native Codex is contractually mandatory only for NFR-prefixed security gates with countersignature requirements (e.g. Init 5 NFR5-SEC-2) and Story 31.1 explicitly disclaims NFR-SECURITY adjacency (§ Story line 14 + § Threat-vector enumeration), so a labeled Hermes `gpt-5.5` delegate fallback was used and labeled honestly in the new `### Review Findings` subsection (no native-Codex impersonation). Round-7 review flagged one [Important] finding — `SpoolsService.refresh_summary` lock release was not ownership-safe under TTL-expiry race (unconditional DEL of `spools:poll-lock` could delete a second worker's freshly-acquired lock after the 90s lease expired). Patched in `82b4e21` via per-refresh `secrets.token_hex(16)` token + WATCH/MULTI/EXEC compare-and-delete release + new regression test `test_service_refresh_summary_lock_release_is_ownership_safe_under_ttl_expiry_race` (verified red against pre-fix code, green after). Round-7b review of `82b4e21` returned **APPROVED — no critical/important/minor findings**. Gates re-run after `82b4e21`: `ruff format --check .` PASS, `ruff check .` PASS, `pytest tests/test_spools.py -q` → **18 passed / 1 skipped**, env-gated `SPOOLMAN_LIVE_TEST=1 SPOOLMAN_URL=http://192.168.2.190:7912 pytest tests/test_spools.py -q` → **19 passed**, full backend `pytest -q` → **938 passed / 1 skipped / 1453 warnings** (project-wide non-blocking baseline; Story 31.1 introduces zero new warnings); AC-12 grep invariants re-confirmed clean. Triage: 0 decision-needed, 1 patch (already applied in `82b4e21`), 0 deferred, 0 dismissed. All findings resolved on this branch. T8.2 + T11.3 + T11.4 satisfied by `b932a9c` (OD8 trailer verbatim; conventional-commit scope verbatim; Story 31.2 depends-on lift note in body). Story file `Status:` flipped `review → done`. Sprint-status `31-1-backend-spoolman-client-cache-poll` flipped `review → done`. No production code touched in this close-out pass. |
| 2026-05-29 | claude-opus-4-7 (1M context) via bmad-dev-story | **Dev-story close-out pass (record-keeping only — no code change).** Re-verified branch state: working tree carries only the Story 31.1 surface (6 new files in `apps/api/app/modules/spools/` + `apps/api/app/workers/spoolman_poll.py` + `apps/api/tests/test_spools.py`; 4 modified files `apps/api/app/core/config.py`, `apps/api/app/workers/__init__.py`, `apps/api/tests/test_config.py`, `infra/env.example`). AC-12 invariants confirmed: `git diff main -- apps/api/app/main.py` returns ZERO diff (`_PUBLIC_ROUTES` allowlist preserved); `git diff main -- apps/api/app/modules/share/router.py` returns ZERO diff (NFR10 credentialless surface untouched); `grep -rnE "current_(user\|admin\|member_or_admin\|admin_or_agent)" apps/api/app/modules/spools/` returns ZERO matches (no auth deps — Story 31.1 mounts no routes). AC-7 magic-constant contract comments confirmed in code: `client.py` carries `because "..."` annotations on `5.0` (httpx timeout), `3` (`_CIRCUIT_FAILURE_THRESHOLD`), `30.0` (`_CIRCUIT_OPEN_SECONDS`); `service.py` carries them on `_CACHE_TTL_SECONDS=30`, `_LOCK_EXPIRY_SECONDS=90`, plus the 3 byte-pinned key constants per AC-4; `workers/__init__.py` carries the `60`s cadence rationale on `cron(poll_spoolman_summary, second={0})`. Test evidence pinned in the Debug Log References section above: targeted `apps/api/.venv/bin/pytest tests/test_spools.py -q` → **17 passed / 1 skipped**; full backend suite `apps/api/.venv/bin/pytest -q` → **937 passed / 1 skipped** (Story 31.1 introduces zero new warnings; 1453 warnings is the pre-existing project baseline); env-gated `SPOOLMAN_LIVE_TEST=1` live smoke → **1 passed** after the round-6 nested vendor/filament Pydantic fix-up; OD8 LAN-only bind on `.190` confirmed by `docker inspect`. No open code-side blockers. Sprint-status row `31-1-backend-spoolman-client-cache-poll` flipped `ready-for-dev → review` in `_bmad-output/implementation-artifacts/sprint-status.yaml`. Remaining merge gate: T8.2 / T11.3 / T11.4 — the 3d-portal merging commit MUST carry the verbatim trailer `OD8 close-out: Spoolman bind verified LAN-only on .190 (configs-side)`; recommended next workflow step is `bmad-code-review` (Codex routing `gpt-5.4-mini`) followed by ff-merge to `main`. Status stays **review**. |
