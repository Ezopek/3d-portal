"""Contract regression tests for runbook ↔ OpenAPI consistency.

Locks the claims the `/agent-runbook` markdown makes about the OpenAPI surface
so future schema/description drift fails at PR time rather than during an
external bootstrap-surface review.

Sources of truth:
- `docs/agents-add-model-runbook.md` (the markdown baked into the API image at
  build time via `apps/api/Dockerfile:26`)
- `app.openapi()` (the spec served at `/api/openapi.json`)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.main import create_app

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNBOOK_SRC = _REPO_ROOT / "docs" / "agents-add-model-runbook.md"


@pytest.fixture(scope="module")
def openapi_spec() -> dict:
    return create_app().openapi()


@pytest.fixture(scope="module")
def runbook_text() -> str:
    return _RUNBOOK_SRC.read_text(encoding="utf-8")


# --- OpenAPI surface ------------------------------------------------------


def test_user_role_enum_is_emitted_to_components_schemas(openapi_spec: dict):
    schemas = openapi_spec["components"]["schemas"]
    assert "UserRole" in schemas, (
        "UserRole missing from components.schemas — runbook claims it is "
        "emitted there (see docs/agents-add-model-runbook.md § Endpoint "
        "Discovery via OpenAPI → Enums)"
    )
    role_schema = schemas["UserRole"]
    assert set(role_schema.get("enum", [])) == {"admin", "agent", "member"}


def test_me_response_role_references_user_role_enum(openapi_spec: dict):
    me = openapi_spec["components"]["schemas"]["MeResponse"]
    role_prop = me["properties"]["role"]
    # Pydantic + FastAPI emit either a top-level $ref or an allOf wrapper for
    # enum-typed fields depending on whether the field is nullable / has a
    # default. Accept any shape that ultimately points at #/components/schemas/UserRole.
    ref = role_prop.get("$ref") or (role_prop.get("allOf") or [{}])[0].get("$ref")
    assert ref == "#/components/schemas/UserRole", (
        f"MeResponse.role should reference UserRole; got {role_prop!r}"
    )


def test_render_description_uses_actual_thumbnail_field_name(openapi_spec: dict):
    op = openapi_spec["paths"]["/api/admin/models/{model_id}/render"]["post"]
    description = op.get("description", "")
    assert "thumbnail_file_id" in description, (
        "render description should reference the actual ModelDetail field "
        "name `thumbnail_file_id`, not the bare `thumbnail`"
    )
    assert "thumbnail field flip" not in description, (
        "render description still contains the legacy `thumbnail field flip` "
        "phrasing — should be `thumbnail_file_id field flip`"
    )


# --- Runbook markdown contents -------------------------------------------


def test_runbook_fetch_strategy_table_includes_cults3d(runbook_text: str):
    # The host→fetch-strategy table sits above the host→source-enum table.
    # Slice out everything before the enum table to scope the check.
    head, sep, _tail = runbook_text.partition("### Host → `source` enum mapping")
    assert sep, "runbook structure changed — missing enum mapping section header"
    assert "cults3d.com" in head, (
        "cults3d.com missing from the host→fetch-strategy table in the runbook"
    )
    # The strategy column should mark this row as browser-driven, matching the
    # other browser-only sources (thangs/thingiverse/makerworld/crealitycloud).
    cults_lines = [line for line in head.splitlines() if "cults3d.com" in line]
    assert any("agent-browser" in line for line in cults_lines), (
        f"cults3d.com row should use the agent-browser CLI strategy; rows: {cults_lines!r}"
    )


def test_runbook_browser_only_caption_counts_five_sources(runbook_text: str):
    assert "five browser-only sources" in runbook_text, (
        "Caption below the fetch-strategy table should now read "
        "'five browser-only sources' (was 'four') after the cults3d.com row landed"
    )
    assert "four browser-only sources" not in runbook_text, (
        "Stale 'four browser-only sources' caption remains — bump to 'five'"
    )


def test_runbook_login_section_makes_user_envelope_explicit(runbook_text: str):
    # The login section is the first paragraph after the curl block under
    # § "Get an access cookie" / similar. Look for the response-shape sentence.
    # We don't enforce exact wording — either an explicit `{user: {...}}` /
    # `{"user": ...}` mention or a `jq .user.*` example is acceptable.
    head, _sep, _tail = runbook_text.partition("### Reusing the cookie")
    assert "user" in head, "login section structure changed unexpectedly"
    envelope_mentioned = any(
        token in head
        for token in ("{user:", '{"user"', "jq .user.", "`user` wrapper", "user wrapper")
    )
    assert envelope_mentioned, (
        "Login response paragraph should make the `{user: {...}}` envelope "
        "explicit (e.g. mention the `user` wrapper or show `jq .user.email`) "
        "so a literal reader doesn't try `jq .email`."
    )
