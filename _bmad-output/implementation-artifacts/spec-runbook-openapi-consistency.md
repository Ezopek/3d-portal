---
title: 'Runbook ↔ OpenAPI consistency fixes from external review'
type: 'bugfix'
created: '2026-05-16'
status: 'done'
baseline_commit: '53f84624addb024e2c520885ae00182e7ce6bb53'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** External review of the bootstrap surface our portal serves to outside AI agents (`/agent-runbook` + `/api/openapi.json`) surfaced four consistency defects:
- (a) Runbook claims `UserRole` is in `components.schemas` but `MeResponse.role` is bare `str`, so FastAPI never emits the enum.
- (b) `/render` description says `watch the thumbnail field flip non-null` — actual field is `thumbnail_file_id`.
- (c) `cults3d.com` is in the host→source-enum table + the `ModelSource`/`ExternalSource` enums, but absent from the host→fetch-strategy table. Agent has no download instruction.
- (d) Login section says "responds with the user record in the body" without noting the `{user: {...}}` envelope; literal reader hits `jq .email` instead of `jq .user.email`.

**Approach:** Two thin layers. **API:** switch `MeResponse.role: str` to existing `UserRole(StrEnum)` import + rename `thumbnail` → `thumbnail_file_id` in the `/render` description. **Runbook:** add the `cults3d.com` row (browser CLI, same shape as the four existing browser-driven rows), bump the "four browser-only sources" caption to "five", clarify the login-response sentence to reference the `{user: {...}}` envelope.

## Boundaries & Constraints

**Always:**
- Wire-format role values stay `"admin" | "agent" | "member"` — StrEnum serializes to its string. Frontend mirror at `apps/web/src/lib/api-types.ts:10` and tests like `body["user"]["role"] == "admin"` must keep passing without modification.
- Runbook is baked into the API image via `COPY docs/agents-add-model-runbook.md /app/static/agent-runbook.md` (Dockerfile:26). Docs changes ship only after fresh image build + deploy. Do NOT touch `infra/.runbook-fingerprint` — deploy verify regenerates it.
- New `cults3d.com` row matches the four existing browser-driven rows verbatim (`agent-browser` CLI, "Browser session must be logged in already").

**Ask First:**
- If the test suite surfaces ANY regression in auth/login/me tests, OpenAPI contract tests, or the existing `test_runbook.py` — stop and report before adapting tests. The change is intended non-breaking at the wire level; regression = real signal.

**Never:**
- Do NOT touch `crealitycloud.com → other` mapping (intentionally deferred per runbook line 157 → triage-backlog).
- Do NOT add `member` to the runbook prose — the runbook's user-role narrative is agent/admin only; `member` is portal-internal. Emit the enum (all 3 values) to OpenAPI but don't expand runbook copy.
- Do NOT regenerate `apps/web/src/lib/api-types.ts` or the `Role` type — already mirrors the 3-value set; hand-maintained per its docstring.
- Do NOT touch snapshot copies in `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` — refreshed by re-curl after deploy per the onboarding dialog flow.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| OpenAPI exposes UserRole | `GET /api/openapi.json` | `components.schemas.UserRole` exists with `enum: ["admin","agent","member"]` (StrEnum order); `MeResponse.role` references `#/components/schemas/UserRole` | N/A |
| Login response wire shape | `POST /api/auth/login` w/ valid agent creds | `body["user"]["role"]` is one of the three string values (unchanged from today) | N/A — wire format identical |
| Render description text | `GET /api/openapi.json`, jq `.paths."/api/admin/models/{model_id}/render".post.description` | String contains `thumbnail_file_id` substring; does NOT contain bare `thumbnail field flip` | N/A |
| Runbook fetch-strategy table | `GET /agent-runbook`, grep `cults3d.com` | One row with `cults3d.com` + `agent-browser` CLI strategy + browser-session auth note | N/A |
| Runbook caption count | `GET /agent-runbook`, grep `browser-only sources` | Caption reads "five browser-only sources", not "four" | N/A |
| Runbook login sentence | `GET /agent-runbook`, grep paragraph at "responds with" | Sentence makes `{user: {...}}` envelope explicit (e.g. "responds with `{user: {...}}` in the body" or equivalent) | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/app/modules/auth/models.py` -- `MeResponse.role: str` → `role: UserRole` (import from `app.core.db.models._enums`); only file in this module touched.
- `apps/api/app/modules/sot/admin_router.py` -- line 370 string literal `thumbnail` → `thumbnail_file_id` inside the `description=` arg of `@router.post("/models/{model_id}/render", ...)`.
- `docs/agents-add-model-runbook.md` -- two text edits: (1) lines 133-141 (host→fetch-strategy table + caption); (2) line 44 (login response sentence).
- `apps/api/tests/test_auth.py`, `apps/api/tests/test_auth_login_logout.py` -- existing assertions against `role == "admin"` should still pass; verify, do not modify unless they fail.
- `apps/api/tests/test_runbook.py` -- existing `/agent-runbook` route contract tests; no expected change.

## Tasks & Acceptance

**Execution (TDD order — write failing tests first, then turn them green):**
- [x] `apps/api/tests/test_runbook_openapi_consistency.py` -- new test module covering the three OpenAPI-side I/O scenarios (UserRole emitted to `components.schemas`, `MeResponse.role` refs `#/components/schemas/UserRole`, render description contains `thumbnail_file_id` and does NOT contain `thumbnail field flip`). Rationale: locks the runbook claim's contract so future drift is caught at PR time. Expected red on first run.
- [x] `apps/api/app/modules/auth/models.py` -- import `UserRole` from `app.core.db.models._enums`; change `MeResponse.role: str` to `role: UserRole`. Rationale: lands `UserRole` in `components.schemas` and makes the runbook's claim true. Turns first 2 test cases green.
- [x] `apps/api/app/modules/sot/admin_router.py` -- in the `/models/{model_id}/render` POST `description=` string (around line 370), replace `the \`thumbnail\` field flip non-null` with `the \`thumbnail_file_id\` field flip non-null`. Rationale: matches the actual `ModelDetail` field name and runbook step 11. Turns 3rd test case green.
- [x] `docs/agents-add-model-runbook.md` -- in the host→fetch-strategy table (~line 133), insert a row for `cults3d.com` matching the existing four browser-driven rows in shape (`agent-browser` CLI, browser session must be logged in). Update the caption sentence below the table from "the four browser-only sources" to "the five browser-only sources".
- [x] `docs/agents-add-model-runbook.md` -- in the login flow section (~line 44), tighten "responds with the user record in the body" to make the `{user: {...}}` envelope explicit (e.g. "responds with `{"user": {...}}` — note the wrapper, so it's `jq .user.email` not `jq .email` — and sets two cookies:").

**Acceptance Criteria:**
- Given a fresh `GET /api/openapi.json`, when parsed, then `components.schemas.UserRole.enum` equals `["admin", "agent", "member"]` and `components.schemas.MeResponse.properties.role` references `#/components/schemas/UserRole`.
- Given a fresh `GET /api/openapi.json`, when inspecting the `/api/admin/models/{model_id}/render` POST description, then it contains `thumbnail_file_id` and does NOT contain the bare phrase `thumbnail field flip`.
- Given a fresh `GET /agent-runbook`, when grepped for `cults3d.com`, then it appears at least once in the host→fetch-strategy table with `agent-browser` strategy.
- Given a fresh `GET /agent-runbook`, when reading the login section, then the sentence describing the response body explicitly indicates the `{user: {...}}` envelope (mention of "user" wrapper or `jq .user.<x>` example acceptable).
- Given the existing `apps/api/tests/` suite, when run after the change, then all tests pass without modification.
- Given `ruff check` + `ruff format --check` on `apps/api/`, when run, then both report clean.

## Spec Change Log

(empty — populated during step-04 review loops)

## Verification

**Commands:**
- `cd apps/api && uv run ruff check . && uv run ruff format --check .` -- expected: clean exit on both.
- `cd apps/api && uv run pytest -x` -- expected: all tests pass; the new `test_runbook_openapi_consistency.py` cases pass alongside untouched suites.
- `cd apps/api && uv run python -c "from app.main import create_app; import json; app = create_app(); spec = app.openapi(); print(json.dumps({'UserRole': spec['components']['schemas'].get('UserRole'), 'me_role_ref': spec['components']['schemas']['MeResponse']['properties']['role']}, indent=2))"` -- expected: prints `UserRole` schema with enum `["admin","agent","member"]` and `me_role_ref` shows `$ref` to `#/components/schemas/UserRole`.

**Manual checks (if no CLI):**
- Open `docs/agents-add-model-runbook.md` and verify: line ~134 has `cults3d.com` row; caption reads "five browser-only sources"; login paragraph references the `{user: {...}}` envelope shape.

## Suggested Review Order

**API surface — UserRole emission**

- Entry point: wires the existing enum into the auth response so FastAPI emits it to `components.schemas`.
  [`models.py:18`](../../apps/api/app/modules/auth/models.py#L18)

- Supporting import — `UserRole` already lives in the shared enums module; reused as-is.
  [`models.py:6`](../../apps/api/app/modules/auth/models.py#L6)

**OpenAPI description correctness**

- One-character intent: aligns the `/render` poll guidance with the actual `ModelDetail.thumbnail_file_id` field name + runbook step 11.
  [`admin_router.py:370`](../../apps/api/app/modules/sot/admin_router.py#L370)

**Runbook content — bootstrap surface for external agents**

- Login response shape — makes the `{user: {...}}` envelope explicit so a literal reader uses `jq .user.email` not `jq .email`.
  [`agents-add-model-runbook.md:44`](../../docs/agents-add-model-runbook.md#L44)

- Fetch-strategy row for `cults3d.com` — closes the gap between the source-enum table and the download-strategy table.
  [`agents-add-model-runbook.md:139`](../../docs/agents-add-model-runbook.md#L139)

- Caption bump from "four" → "five" browser-only sources, matching the new row count.
  [`agents-add-model-runbook.md:142`](../../docs/agents-add-model-runbook.md#L142)

**Regression lock (peripheral)**

- New contract tests pin all six runbook ↔ OpenAPI claims so future drift fails at PR time, not at the next external review.
  [`test_runbook_openapi_consistency.py:1`](../../apps/api/tests/test_runbook_openapi_consistency.py#L1)
