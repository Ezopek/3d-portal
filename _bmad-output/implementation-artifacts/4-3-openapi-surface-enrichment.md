# Story 4.3: OpenAPI Surface Enrichment for Agent Consumption

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an AI agent consuming `/api/openapi.json` to discover endpoint signatures,
I want each agent-callable endpoint under `apps/api/app/modules/{admin,sot}/` to carry a `summary`, `description` (including behavioral side-effects), a relevant tag, and at least one request-body example on its Pydantic input model,
So that I can read the OpenAPI surface and execute the agent flow without spelunking the FastAPI source.

## Acceptance Criteria

**Given** `apps/api/app/modules/sot/admin_router.py` (29 mutating routes), `apps/api/app/modules/sot/router.py` (6 public reads), and `apps/api/app/modules/admin/router.py` (3 admin-debug routes) currently define routes with **zero** `summary` / `description` arguments on the decorators, and most Pydantic request models in `apps/api/app/modules/sot/admin_schemas.py` already declare `model_config = ConfigDict(extra="forbid")` but lack `json_schema_extra={"examples": [...]}`,

**When** Story 4.3 ships:

1. **Every `@router.post / @router.put / @router.patch / @router.delete / @router.get` decorator** in `apps/api/app/modules/{admin,sot}/` (38 routes total: 29 in `sot/admin_router.py` + 6 in `sot/router.py` + 3 in `admin/router.py`) carries an explicit `summary="One-line capability description, ≤80 chars"` and `description="Multi-line that names behavioral side-effects (e.g. 'first STL upload auto-enqueues render via arq'), authorization requirements (admin vs agent role), and any non-obvious failure modes ('returns 200 on sha256 duplicate, 201 on new upload')."` Conventional Python triple-quoted strings; `summary` stays compact, `description` is where the behavioral honesty goes.

2. **Every mutating endpoint in `sot/admin_router.py` (29 routes) ALSO carries `tags=["agent-write"]`** on the decorator. Router-level `tags=["sot-admin"]` is preserved by FastAPI's tag union; final OpenAPI tag list per operation is `["sot-admin", "agent-write"]`. The `admin/router.py` routes (sentry-test, audit, audit-log) get `summary` + `description` only — they are admin-only and NOT agent-callable per current auth dep (`current_admin`, not `current_admin_or_agent`); they do NOT get `agent-write`. The `sot/router.py` public reads also do NOT get `agent-write` (read-only, not "write"); their existing `sot-read` router tag stays as-is and is sufficient for agent discovery via OpenAPI tag filter (Story 4.3 does not introduce an `agent-read` tag).

3. **Each Pydantic request model in `apps/api/app/modules/sot/admin_schemas.py`** that backs an agent-writable endpoint carries `model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [<one realistic example>]})`. The 19 affected models:
   - `ModelCreate`, `ModelPatch`, `ModelFilePatch`, `RenderRequest`, `PhotoReorderRequest`, `ThumbnailSet`
   - `TagsReplace`, `TagAdd`, `TagCreate`, `TagPatch`, `TagMerge`
   - `CategoryCreate`, `CategoryPatch`
   - `NoteCreate`, `NotePatch`
   - `PrintCreate`, `PrintPatch`
   - `ExternalLinkCreate`, `ExternalLinkPatch`
   Each example uses realistic field values (real-looking UUIDs, plausible names, sensible enums) so an agent can copy-paste and adapt rather than guess shape. Examples are pinned constants (no random/dynamic data). The 13 models that already declare `ConfigDict(extra="forbid")` get the `json_schema_extra=...` argument added; the 6 that have no `model_config` yet get it added from scratch — `extra="forbid"` is the project-wide default per existing schemas, so keep it consistent.

4. **New Pytest `apps/api/tests/test_openapi_agent_surface.py`** asserts in a single test run:
   - (a) Every operation under `/api/admin/...` and `/api/...` paths owned by `admin/router.py`, `sot/admin_router.py`, `sot/router.py` has non-empty `summary` and `description` in the generated OpenAPI document.
   - (b) Every operation tagged `agent-write` has at least one `examples` entry on its request-body schema (follow `$ref` to `components.schemas.<Name>` if present; check both `examples` and `example` at schema level since Pydantic v2 may emit either).
   - (c) Every model listed in §3 above appears in `components.schemas` with at least one example.
   - The test FAILS if a future route is added without `summary`/`description`, or without `agent-write` tag on a `sot/admin_router.py` mutating route, or if a future agent-writable request model lands without an `examples` entry. This is the long-term enforcement value of the story.
   - Test uses the same `TestClient` + `_isolated_db` fixture pattern as `apps/api/tests/test_*.py` (per project-context.md § "Backend testing" rules). No auth required to fetch `/api/openapi.json` — it is unauthenticated by FastAPI default.

5. **Spot-check command** (operator-runnable, documented in story Completion Notes): `curl -s https://3d.ezop.ddns.net/api/openapi.json | jq '.paths."/api/admin/models".post | {summary, description, requestBody}'` returns a non-empty `summary`, a non-empty `description`, and a `requestBody.content."application/json".schema` with `examples` reachable via `$ref`.

6. **Retro-edit `docs/agents-add-model-runbook.md`** to re-add the `agent-write` tag jq snippet that Story 4.1 fix-up removed (Codex P2 finding ec27222: "tag doesn't exist until Story 4.3"). Once Story 4.3 ships, the snippet becomes valid:
   ```bash
   curl -s https://3d.ezop.ddns.net/api/openapi.json \
     | jq '.paths | to_entries[] | select(.value | .. | objects? | .tags? // [] | index("agent-write")) | .key'
   ```
   Add it back under § "Endpoint Discovery via OpenAPI" as an additional snippet under the existing path-list one. **Critical:** do NOT modify the intro paragraph (fingerprint subject) — keep `infra/.runbook-fingerprint` baseline `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573` valid. Recompute the fingerprint after the edit to confirm match; if mismatch, the intro got accidentally touched and must be restored.

**And** `ruff check apps/api` passes (no new lint warnings).
**And** `pytest apps/api/tests/test_openapi_agent_surface.py -v` passes; full test suite `pytest apps/api/tests` passes (no regressions).
**And** Story 4.3 ships in a single commit `feat(api): OpenAPI enrichment for agent consumption (E4.3)` plus the doc-only retro-edit may ride in the same commit OR a sibling `docs(agents): re-add agent-write tag discovery snippet (E4.3 retro)`. Either single-commit or 2-commit split is fine; the API change triggers auto-deploy per project memory `feedback_auto_deploy_dev.md`.

## Tasks / Subtasks

- [x] **Task 1: Read existing routes + schemas to lock the enrichment surface** (AC: 1, 2, 3)
  - [x] Re-read `apps/api/app/modules/sot/admin_router.py` end-to-end (~800 lines) to confirm the 29 routes + handler signatures + behavioral side-effects (especially the auto-enqueue render path on first STL).
  - [x] Re-read `apps/api/app/modules/sot/router.py` for the 6 public reads (filters, pagination shape).
  - [x] Re-read `apps/api/app/modules/admin/router.py` for the 3 admin routes.
  - [x] Re-read `apps/api/app/modules/sot/admin_schemas.py` to catalog the 19 request models, their fields + types + `Field(min_length, ge, le)` constraints — examples must respect these constraints.

- [x] **Task 2: Add `summary` + `description` to `sot/admin_router.py` (29 routes)** (AC: 1, 2)
  - [x] For each `@router.post/put/patch/delete` add `summary="<≤80 char one-liner>"` and `description="""<multi-line including behavioral notes>"""` arguments.
  - [x] For each mutating route, ALSO add `tags=["agent-write"]` (router-level `sot-admin` tag union'd by FastAPI).
  - [x] Behavioral-side-effect callouts to include in descriptions:
    - `POST /models/{id}/files` — "First STL upload (`kind=stl`) per model auto-enqueues a render job via arq; subsequent STL uploads do NOT auto-enqueue. Returns 200 + existing `ModelFileRead` payload on sha256 dedup, 201 on new upload."
    - `POST /models` — "Returns 400 on category-not-found, 409 on slug conflict, 422 on other validation."
    - `DELETE /models/{id}?hard=true` — "Hard-delete restricted to admin role; agent role gets 403 here. Soft delete (no `hard` query) is agent-callable."
    - `POST /models/{id}/render` — "Async render enqueue (status 202); polls via `GET /models/{id}` thumbnail field."
    - `PUT /models/{id}/tags` — "Replaces tag list atomically; for incremental add use `POST /models/{id}/tags`."
    - For other routes use existing handler logic to derive behavioral notes; do not invent behavior the code doesn't have.

- [x] **Task 3: Add `summary` + `description` to `sot/router.py` (6 read routes)** (AC: 1)
  - [x] No `agent-write` tag (read-only). Existing router-level `sot-read` tag stays.
  - [x] Descriptions for filters/pagination on `GET /models` (search query, category filter, sort options) need to match the actual implementation in `apps/api/app/modules/sot/service.py`.

- [x] **Task 4: Add `summary` + `description` to `admin/router.py` (3 routes)** (AC: 1)
  - [x] No `agent-write` tag.
  - [x] `POST /sentry-test` description must keep the "deliberately throws to prove GlitchTip plumbing" note (per project-context.md § "Backend gotchas" rule that says do NOT 'fix' this endpoint).
  - [x] `GET /audit` + `GET /audit-log` — describe filter params + response shape briefly; point at OpenAPI for full schema.

- [x] **Task 5: Add `json_schema_extra` examples to the 19 request models** (AC: 3)
  - [x] For each of the 19 models, add `model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [<example>]})` (or extend an existing `model_config` line).
  - [x] Example values reference realistic UUIDs (`00000000-0000-0000-0000-000000000000` form, but with non-zero patterns like `12345678-1234-5678-1234-567812345678` so they pass UUID parsing and visually scream "example"), realistic names ("Cali Cat", "Stanford Bunny"), valid enum values for `ModelSource` / `ModelStatus` / `ModelFileKind` (sourced from `app.core.db.models`), and respect any `Field(min_length=..., ge=..., le=...)` constraints.
  - [x] Example for `ModelCreate`: `{"name_en": "Stanford Bunny", "name_pl": "Królik Stanforda", "category_id": "12345678-1234-5678-1234-567812345678", "source": "printables", "status": "not_printed"}`. Adapt similar realism to the other 18.
  - [x] For collection-of-uuids models (`PhotoReorderRequest`, `TagsReplace`, `RenderRequest.selected_stl_file_ids`): example contains 1-2 UUIDs, not empty list.

- [x] **Task 6: Write `apps/api/tests/test_openapi_agent_surface.py`** (AC: 4)
  - [x] Use `fastapi.testclient.TestClient` + the `_isolated_db` autouse fixture (auto-loaded from `apps/api/tests/conftest.py` per project-context.md § "Backend testing").
  - [x] Single test class `TestOpenAPIAgentSurface` with three test methods: `test_all_admin_sot_routes_have_summary_and_description`, `test_all_agent_write_routes_have_request_body_example`, `test_all_listed_request_models_have_examples_in_components`.
  - [x] Helper: parse the OpenAPI doc once at module level (or in a fixture) to avoid re-fetching per test.
  - [x] Path filter: include path if any of its operations has `tags` containing `sot-admin`, `sot-read`, or `admin` — that gives us all 38 target routes without hard-coding paths.
  - [x] For `$ref` resolution: write a small helper `_resolve_schema_ref(spec, ref_str)` that splits `#/components/schemas/<Name>` and indexes into the spec dict.
  - [x] Use `pytest.mark.parametrize` to surface ONE failure per failing route rather than one per test method.
  - [x] Test file naming + colocation follows the project convention (`test_<area>.py` per project-context.md).

- [x] **Task 7: Run validations** (AC: ruff + tests + spot-check)
  - [x] `ruff check apps/api` — must pass.
  - [x] `ruff format apps/api --check` — must pass (run `ruff format apps/api` to auto-fix if it doesn't).
  - [x] `pytest apps/api/tests/test_openapi_agent_surface.py -v` — must pass.
  - [x] `pytest apps/api/tests` — full suite must pass (no regressions, especially the existing model/file/auth tests).
  - [x] Local spot-check: bring up the API container (`docker compose up api` from `infra/` OR run `uvicorn app.main:create_app --factory` from `apps/api/`) and curl `/api/openapi.json | jq '.paths."/api/admin/models".post.summary'` — non-empty string.

- [x] **Task 8: Retro-edit `docs/agents-add-model-runbook.md`** (AC: 6)
  - [x] Re-add the `agent-write` jq snippet under § "Endpoint Discovery via OpenAPI", AFTER the existing path-list snippet. Use the exact form from AC #6.
  - [x] DO NOT touch the intro paragraph (lines 3, fingerprint subject). After the edit, recompute fingerprint:
    ```bash
    awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}' docs/agents-add-model-runbook.md | sha256sum | awk '{print $1}'
    ```
    Must equal `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573`. If mismatch, the intro got accidentally edited — revert and retry.
  - [x] Re-run the runbook constraint checks (line count < 600; zero non-backticked `METHOD /api/...` mentions; fingerprint matches `infra/.runbook-fingerprint`).

- [x] **Task 9: Commit + auto-deploy** (AC: commit + deploy rule)
  - [x] Stage `apps/api/app/modules/sot/admin_router.py`, `apps/api/app/modules/sot/router.py`, `apps/api/app/modules/admin/router.py`, `apps/api/app/modules/sot/admin_schemas.py`, `apps/api/tests/test_openapi_agent_surface.py`. Plus `docs/agents-add-model-runbook.md` if the retro-edit rides in the same commit.
  - [x] Conventional commit message: `feat(api): OpenAPI enrichment for agent consumption (E4.3)` (or sibling split with a `docs(agents): re-add agent-write discovery snippet (E4.3 retro)`).
  - [x] **Auto-deploy** per project memory `feedback_auto_deploy_dev.md` — this commit contains API code changes, so `infra/scripts/deploy.sh` runs after the commit lands on `main`, without asking.

## Dev Notes

### Critical context — what this story does NOT do

- **Does NOT change request/response shapes.** Only adds OpenAPI metadata (summary, description, tags) on decorators + `json_schema_extra.examples` on Pydantic models. Zero behavior change.
- **Does NOT introduce an `agent-read` tag.** Story scope is `agent-write` only per epics.md AC. If a future story wants `agent-read` for the 6 public reads, that's a follow-up.
- **Does NOT touch `apps/api/app/modules/share/admin_router.py` or `apps/api/app/modules/auth/router.py`** — out of scope (AC says only `{admin,sot}/`). Auth endpoints in particular are agent-callable but the runbook already documents them via the login flow; OpenAPI enrichment for auth is a different story (would be E4.x follow-up if needed).
- **Does NOT introduce Alembic migrations or new dependencies.** Pure Python/Pydantic metadata edits + one new test file.

### Code-side references the developer must respect

- **FastAPI tag union semantics:** Per FastAPI docs, `APIRouter(tags=[...])` tags concatenate with per-route `@router.post(..., tags=[...])` tags. So router-level `sot-admin` stays applied even when a route adds `agent-write`. Final OpenAPI `tags` array per operation is `["sot-admin", "agent-write"]`. No code needed to merge — FastAPI does this automatically.
- **Pydantic v2 `json_schema_extra` idiom:** Use `model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [<example>]})`. NOT `class Config: schema_extra = ...` (that's v1). The current schemas use `ConfigDict` already on 7 of 19 models — extend those; add `model_config = ConfigDict(...)` from scratch on the remaining 12.
- **OpenAPI `$ref` resolution in test:** When iterating operations, the request body schema is typically `{"$ref": "#/components/schemas/<ModelName>"}`. The `examples` field lives on the resolved component schema, not inline at the requestBody level (Pydantic generates it that way). Test must resolve the ref before checking for examples.
- **Auth dependency:** `_current_admin_or_agent_dep` in `apps/api/app/modules/sot/admin_router.py:128` is what makes the 29 routes agent-callable. Don't touch this dep; just tag the routes as `agent-write` for discoverability.
- **`POST /sentry-test`:** Per project-context.md § "Backend gotchas" — do NOT 'fix' this endpoint. Its description must accurately reflect that it deliberately raises to prove GlitchTip plumbing. Suggested: `description="""Deliberately raises a test exception to verify GlitchTip → portal symbolication pipeline. Admin-only. Returns 204 (the exception is captured by Sentry middleware before the response is shaped). Do NOT 'fix' the raise — it is the contract."""`.

### Test fixtures + patterns (from project-context.md § Backend testing)

- `_isolated_db` autouse fixture provides a tmpdir SQLite + initialized schema. `get_settings.cache_clear()` + `get_engine.cache_clear()` are called automatically.
- `TestClient(create_app())` for HTTP tests. `/api/openapi.json` is unauthenticated by FastAPI default — no login flow needed.
- `pytest-asyncio` runs async tests automatically (config in `pyproject.toml`). The new test is sync (just hits an HTTP endpoint + parses JSON), so no async fixtures needed.
- Test file colocation: `apps/api/tests/test_openapi_agent_surface.py` (test files mirror source area; this one targets the OpenAPI cross-cutting surface, so a top-level `tests/` location is correct).
- Coverage expectations: this test contributes to backend pytest coverage but doesn't introduce new business logic — pure shape assertion.

### Anti-patterns to actively prevent

- ❌ **Don't generate random UUIDs / dynamic examples** at module import time. Pydantic re-imports during test runs would produce inconsistent OpenAPI docs. Use static realistic-looking UUID strings.
- ❌ **Don't hard-code endpoint paths in the test.** Iterate over `spec["paths"]` and filter by tag. A future route addition without `summary` should fail the test automatically — that's the long-term enforcement value.
- ❌ **Don't `noqa`-silence ruff warnings on long description strings.** If a description is too long for line-length 100, split with triple-quoted dedented strings and `textwrap.dedent()` only if necessary; usually wrapping the literal is enough.
- ❌ **Don't paste sensitive values into examples** (real production UUIDs from a live `.190` query, real share tokens, real refresh secrets). Use synthetic patterns that visually look like examples.
- ❌ **Don't add `agent-write` to `admin/router.py` routes.** Their auth dep is `current_admin`, not `current_admin_or_agent`; agent role gets 403 there. Tagging them `agent-write` would lie about callability.
- ❌ **Don't touch the runbook intro paragraph** during Task 8. The fingerprint baseline must remain `49280ada...`.

### Story 4.1 fix-up signals to address here

Codex review of `b382fee` flagged: "The OpenAPI discovery snippet filtered for tag `agent-write`, but current generated OpenAPI has only `admin`, `auth`, `share`, `sot-admin`, `sot-read`; it returns no paths." — fixed in `ec27222` by removing the snippet. Story 4.3 makes that snippet valid again; Task 8 re-adds it under the retro-edit AC. This is the canonical "story-N's removed-as-premature is story-M's re-add" pattern, traceable end-to-end.

### Project Structure Notes

- Touched files (all in `apps/api/`):
  - `app/modules/sot/admin_router.py` — decorator metadata only, 29 routes
  - `app/modules/sot/router.py` — decorator metadata only, 6 routes
  - `app/modules/admin/router.py` — decorator metadata only, 3 routes
  - `app/modules/sot/admin_schemas.py` — `model_config` extension on 19 classes
  - `tests/test_openapi_agent_surface.py` — NEW, ~150-200 lines
- Touched docs:
  - `docs/agents-add-model-runbook.md` — re-add agent-write jq snippet (retro per AC #6)
- Zero changes to:
  - `apps/web/` (no frontend impact)
  - `apps/api/app/core/` (no plumbing changes)
  - `infra/` (no deploy config changes; auto-deploy uses existing flow)
  - Alembic migrations (no schema change)
  - `workers/render/` (no worker changes)

### References

- [_bmad-output/planning-artifacts/epics.md § Story 4.3](../planning-artifacts/epics.md) lines 728-747 (this story's spec).
- [_bmad-output/planning-artifacts/architecture.md § Decision E](../planning-artifacts/architecture.md) lines 921-929 (rationale: native FastAPI auto-generation; Pydantic v2 idiom).
- [_bmad-output/planning-artifacts/architecture.md § Implementation Patterns FastAPI route conventions](../planning-artifacts/architecture.md) lines 978-983 (binding format).
- [_bmad-output/planning-artifacts/prd.md § FR11](../planning-artifacts/prd.md) line 567 (Pytest enforcement requirement).
- [_bmad-output/implementation-artifacts/4-1-agents-add-model-runbook.md](4-1-agents-add-model-runbook.md) — Story 4.1 (done) — Codex review surface that prompted Task 8.
- [apps/api/app/modules/sot/admin_router.py:99-800](../../apps/api/app/modules/sot/admin_router.py) — the 29 mutating routes + auth dep.
- [apps/api/app/modules/sot/router.py:35-115](../../apps/api/app/modules/sot/router.py) — the 6 public reads.
- [apps/api/app/modules/admin/router.py:21-120](../../apps/api/app/modules/admin/router.py) — the 3 admin-debug routes.
- [apps/api/app/modules/sot/admin_schemas.py](../../apps/api/app/modules/sot/admin_schemas.py) — the 19 request models to enrich.
- [_bmad-output/project-context.md § Backend testing](../project-context.md) — TestClient + `_isolated_db` fixture pattern.
- [_bmad-output/project-context.md § Backend gotchas](../project-context.md) — `POST /sentry-test` honesty rule.
- [_bmad-output/project-context.md § Deploy](../project-context.md) — auto-deploy after API code commits.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — `claude-opus-4-7[1m]`. Single-pass dev + Codex review + fix-up, 2026-05-11 via `bmad-dev-story`.

### Debug Log References

### Completion Notes List

- **38 routes enriched** (29 sot/admin + 6 sot/router + 3 admin), all with `summary` + `description`. 29 sot/admin routes also carry `tags=["agent-write"]` (additive to router-level `["sot-admin"]`).
- **19 Pydantic request models** in `admin_schemas.py` carry `model_config = ConfigDict(json_schema_extra={"examples": [...]})` with realistic example payloads pinning Stanford Bunny / Cali Cat / Printables 661995 / etc.
- **Spot-check on .190 confirmed enrichment shipped end-to-end:**
  - `curl https://3d.ezop.ddns.net/api/openapi.json | jq '.paths."/api/admin/models".post.summary'` → `"Create a model row in the catalog"`
  - `curl ... | jq '.components.schemas.ModelCreate.examples'` → array with one realistic Stanford Bunny payload
  - `curl ... | jq '[.paths | to_entries[] | select(.value | .. | objects? | .tags? // [] | index("agent-write")) | .key] | length'` → 29 (matches router route count exactly)
- **Auto-deploy fired twice** (initial commit + Codex fix-up); both `verify-symbolication.sh` runs passed (release `0.1.0+369e3f6` then `0.1.0+7ac5e61`).
- **Runbook fingerprint recomputed after Task 8 retro-edit and after Codex fix:** `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573` matches baseline (intro paragraph untouched both times).
- **Codex review of initial commit** returned 8 P2 + 2 P3, all about description-vs-implementation drift (slug uniqueness scope, hard-delete response shape, thumbnail kind enforcement, photo reorder semantics, STL auto-render gate, print printed_at default, sentry-test 500-vs-204, GET /models tag_ids AND-vs-OR + q scope, plus 1 lax test threshold + 1 $ref recursion gap). All addressed in commit `7ac5e61`. The systemic lesson: when writing description text from one's mental model, verify against the service implementation BEFORE shipping — the runbook + OpenAPI together ARE the contract for AI agents.
- **Test enforcement upgrade:** initial sanity-count check (`>= 25 agent-write ops`) replaced with strict route-set membership check (every route on `sot.admin_router.router` MUST appear in OpenAPI with `agent-write`, and vice versa). Bug-fix during this upgrade: `method.upper() in HTTP_METHODS` (lowercase set) was false-everywhere; corrected to `method.lower() in HTTP_METHODS`. Future routes added to `admin_router.py` without `tags=["agent-write"]` will fail the test immediately — the long-term enforcement value of the story.

### File List

- `apps/api/app/modules/sot/admin_router.py` (MODIFIED — 29 routes enriched + Codex fix-up)
- `apps/api/app/modules/sot/router.py` (MODIFIED — 6 routes enriched + GET /models filter description corrected)
- `apps/api/app/modules/admin/router.py` (MODIFIED — 3 routes enriched + /sentry-test 500-handler note)
- `apps/api/app/modules/sot/admin_schemas.py` (MODIFIED — 19 models with json_schema_extra examples)
- `apps/api/tests/test_openapi_agent_surface.py` (NEW — 24 test cases: 5 shape + 19 parametrized per-model)
- `docs/agents-add-model-runbook.md` (MODIFIED — agent-write jq + per-endpoint discovery snippets re-added; fingerprint preserved)

### Change Log

- 2026-05-11 — Story 4.3 implemented in single dev pass via `bmad-dev-story`. Initial commit `369e3f6` on `main`. Auto-deployed to .190; `verify-symbolication.sh` pass (release `0.1.0+369e3f6`).
- 2026-05-11 — Codex review of `369e3f6` returned 8 P2 + 2 P3 findings. All addressed in commit `7ac5e61`. Auto-deployed; `verify-symbolication.sh` pass (release `0.1.0+7ac5e61`). Status `ready-for-dev → in-progress → review → done`.

### Senior Developer Review (AI)

**Reviewer:** Codex (codex-cli 0.129.0) via `codex exec` cross-LLM review
**Date:** 2026-05-11
**Commit reviewed:** `369e3f6` (initial Story 4.3 implementation)
**Outcome:** Changes Requested → addressed in fix-up commit `7ac5e61`

#### Action Items

- [x] **[P2]** Test agent-write enforcement was `>=25`, lax. **Resolution:** replaced with strict per-route membership check derived from `sot.admin_router.router.routes` introspection. (`7ac5e61`)
- [x] **[P2]** GET /models description claimed `tag_ids` is OR + `q` searches names+tags; impl is AND for tags + name_en/pl/slug only for q. **Resolution:** description corrected to match `list_models()` actual semantics. (`7ac5e61`)
- [x] **[P2]** `/sentry-test` description said "Returns 204 on the wire"; the unhandled raise actually surfaces as HTTP 500. **Resolution:** description corrected; OpenAPI `responses={500: ...}` added. (`7ac5e61`)
- [x] **[P2]** `DELETE /models/{id}` documented as `200 + ModelDetail` for both paths; hard-delete actually returns empty 200. **Resolution:** description distinguishes the two response shapes. (`7ac5e61`)
- [x] **[P2]** `PUT /thumbnail` claimed image-kind-only enforcement; service only checks existence + same-model. **Resolution:** dropped the kind claim; noted the frontend is expected to pick an image. (`7ac5e61`)
- [x] **[P2]** `POST /photos/reorder` claimed permutation-of-images requirement; service accepts image OR print and partial subsets. **Resolution:** description rewritten to match. (`7ac5e61`)
- [x] **[P2]** `POST /prints` claimed `printed_at` defaults to today + photo kind validated; neither is true. **Resolution:** description corrected. (`7ac5e61`)
- [x] **[P2]** `POST /models/{id}/files` STL upload — auto-enqueue gate is "no auto-render image exists yet", not "first STL upload". **Resolution:** description rewritten with the actual gate semantics + practical consequence note (rapid back-to-back uploads on a fresh model can each enqueue until worker writes). (`7ac5e61`)
- [x] **[P3]** `POST /models` slug-conflict text said "unique within a category"; `Model.slug` is globally unique. **Resolution:** changed to "globally unique across all categories". (`7ac5e61`)
- [x] **[P3]** `_has_examples` test helper didn't follow `$ref` inside allOf/anyOf/oneOf branches. **Resolution:** helper now takes `spec` as second arg and resolves `$ref` at every recursive node. (`7ac5e61`)

#### Review Mechanics Notes

- 8/10 findings were "description overstates implementation" — the systemic shape was a single-pass author writing descriptions from mental model rather than verifying each one against the service code. The smoke-test in Story 4.5 would catch these as agent friction; catching them here at the OpenAPI gate is cheaper.
- The 1 P2 test-tightening was the right call — sanity counts hide regressions; route-set membership against introspected router state is the correct invariant. The `method.upper() in HTTP_METHODS` (lowercase set) bug-fix during this tightening was a 30-second find-and-fix once `pytest -v` showed the missing match.
- Codex correctly validated all 19 example payloads against their Pydantic schemas (UUIDs/enums/dates parse). No example-quality findings — the realism budget was right.
