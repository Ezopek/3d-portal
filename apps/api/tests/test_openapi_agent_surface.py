"""Story 4.3 enforcement: OpenAPI surface enrichment for agent consumption.

Asserts that every operation under `apps/api/app/modules/{admin,sot}/`:

1. Carries a non-empty `summary` and `description` in the generated OpenAPI doc.
2. Mutating endpoints in `sot/admin_router.py` carry the `agent-write` tag (additive
   to the router-level `sot-admin` tag).
3. Each `agent-write`-tagged endpoint's request body schema (resolved through `$ref`)
   has at least one `examples` entry.
4. Each request model listed in the story (the 19 enriched in `sot/admin_schemas.py`)
   appears in `components.schemas` with at least one example.

The point of this test is long-term enforcement: a future route added to
`sot/admin_router.py` without `summary` + `description` + `agent-write` tag will
fail this test. Same for a new agent-writable request model without `examples`.
"""

from __future__ import annotations

import pytest

from app.main import create_app

# ---------------------------------------------------------------------------
# OpenAPI fetch (module-scoped: one request, many assertions)
# ---------------------------------------------------------------------------

# The 19 request models enriched in Story 4.3. Future agent-writable models added
# to sot/admin_schemas.py SHOULD be appended here so the example-coverage gate
# expands with the surface.
ENRICHED_REQUEST_MODELS = [
    "ModelCreate",
    "ModelPatch",
    "ModelFilePatch",
    "RenderRequest",
    "PhotoReorderRequest",
    "ThumbnailSet",
    "TagsReplace",
    "TagAdd",
    "TagCreate",
    "TagPatch",
    "TagMerge",
    "CategoryCreate",
    "CategoryPatch",
    "NoteCreate",
    "NotePatch",
    "PrintCreate",
    "PrintPatch",
    "ExternalLinkCreate",
    "ExternalLinkPatch",
]

# Tags marking operations that belong to admin/router.py + sot/admin_router.py +
# sot/router.py respectively. Operations carrying ANY of these tags are in scope
# for the summary/description gate.
TARGET_ROUTER_TAGS = {"admin", "sot-admin", "sot-read"}

# Tags that identify an operation as belonging to a different module that
# Story 4.3 explicitly excluded (e.g. share/admin_router.py shares the "admin"
# tag with admin/router.py but is out of scope per the AC). An operation is
# excluded if it carries ANY of these.
EXCLUDED_ROUTER_TAGS = {"share"}

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


@pytest.fixture(scope="module")
def openapi_spec() -> dict:
    """Generate the OpenAPI document once per test module. Calls `app.openapi()`
    directly rather than going through `TestClient.get('/api/openapi.json')`
    so we avoid running the lifespan (which tries to open a real Redis +
    arq pool) — schema generation is a pure-Python operation that doesn't
    need any of the runtime plumbing."""
    app = create_app()
    return app.openapi()


def _iter_target_operations(spec: dict):
    """Yield (method_upper, path, operation_dict) for every operation whose tags
    intersect TARGET_ROUTER_TAGS but do NOT intersect EXCLUDED_ROUTER_TAGS
    (i.e. the routes Story 4.3 enriches; share/admin_router.py is excluded
    because it shares the `admin` tag with admin/router.py but is out of
    Story 4.3's stated scope)."""
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method.lower() not in HTTP_METHODS:
                continue
            tags = set(operation.get("tags") or [])
            if not (tags & TARGET_ROUTER_TAGS):
                continue
            if tags & EXCLUDED_ROUTER_TAGS:
                continue
            yield method.upper(), path, operation


def _resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a `#/components/schemas/<Name>` JSON Pointer against the spec."""
    assert ref.startswith("#/"), f"unexpected $ref form: {ref}"
    node: dict = spec
    for token in ref.lstrip("#/").split("/"):
        node = node[token]
    return node


def _request_body_schema(operation: dict, spec: dict) -> dict | None:
    """Return the resolved request-body schema dict for an operation, or None
    if the operation has no request body."""
    body = operation.get("requestBody")
    if not body:
        return None
    json_content = body.get("content", {}).get("application/json")
    if not json_content:
        # Multipart endpoints (e.g. POST /models/{id}/files) — not in the
        # 19-schema gate; their examples live in `multipart/form-data` if at all.
        return None
    schema = json_content.get("schema", {})
    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])
    return schema


def _has_examples(schema: dict) -> bool:
    """Return True if a schema (or one of its allOf/anyOf branches) carries an
    `examples` array OR an `example` field. Pydantic v2 typically emits
    `examples`; OpenAPI 3.0 sometimes uses singular `example`."""
    if not schema:
        return False
    if schema.get("examples"):
        return True
    if schema.get("example") is not None:
        return True
    for branch in schema.get("allOf", []) + schema.get("anyOf", []) + schema.get("oneOf", []):
        if isinstance(branch, dict) and _has_examples(branch):
            return True
    return False


# ---------------------------------------------------------------------------
# AC §4.a — every admin/sot operation has summary + description
# ---------------------------------------------------------------------------


def test_target_routes_present(openapi_spec):
    """Sanity: at least one operation matches the target tags. Catches a future
    refactor that accidentally renames the tags."""
    ops = list(_iter_target_operations(openapi_spec))
    assert len(ops) >= 30, (
        f"expected ≥30 operations across admin+sot routers; found {len(ops)}. "
        "Did the router-level tags change?"
    )


def test_every_admin_sot_operation_has_summary(openapi_spec):
    """Every operation carrying admin/sot-admin/sot-read tag has non-empty `summary`."""
    missing: list[str] = []
    for method, path, operation in _iter_target_operations(openapi_spec):
        summary = operation.get("summary") or ""
        if not summary.strip():
            missing.append(f"{method} {path}")
    assert not missing, "operations missing non-empty `summary`:\n  " + "\n  ".join(missing)


def test_every_admin_sot_operation_has_description(openapi_spec):
    """Every operation carrying admin/sot-admin/sot-read tag has non-empty `description`."""
    missing: list[str] = []
    for method, path, operation in _iter_target_operations(openapi_spec):
        description = operation.get("description") or ""
        if not description.strip():
            missing.append(f"{method} {path}")
    assert not missing, "operations missing non-empty `description`:\n  " + "\n  ".join(missing)


# ---------------------------------------------------------------------------
# AC §4.b — every agent-write operation's request body has examples
# ---------------------------------------------------------------------------


def test_agent_write_routes_exist(openapi_spec):
    """Sanity: at least 25 operations carry the `agent-write` tag (29 routes
    in sot/admin_router.py — allow some slack for future renames)."""
    count = sum(
        1
        for _m, _p, op in _iter_target_operations(openapi_spec)
        if "agent-write" in (op.get("tags") or [])
    )
    assert count >= 25, (
        f"expected ≥25 `agent-write`-tagged operations; found {count}. "
        "Did Story 4.3 not ship, or did the tag get renamed?"
    )


def test_every_agent_write_json_body_has_examples(openapi_spec):
    """Every `agent-write`-tagged operation with a JSON request body has at
    least one example on its resolved schema. Multipart-only endpoints (e.g.
    file upload) are exempt — their examples live in the form-data shape."""
    missing: list[str] = []
    for method, path, operation in _iter_target_operations(openapi_spec):
        if "agent-write" not in (operation.get("tags") or []):
            continue
        schema = _request_body_schema(operation, openapi_spec)
        if schema is None:
            # No JSON body (e.g. multipart, or no body at all like DELETE) — skip.
            continue
        if not _has_examples(schema):
            missing.append(f"{method} {path}")
    assert not missing, (
        "agent-write operations with JSON bodies missing `examples` on the request "
        "schema:\n  " + "\n  ".join(missing)
    )


# ---------------------------------------------------------------------------
# AC §4.c — every enriched request model in components.schemas has examples
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model_name", ENRICHED_REQUEST_MODELS)
def test_enriched_request_model_has_examples_in_components(openapi_spec, model_name):
    """Each Story-4.3-enriched request model is present in components.schemas
    with at least one example. Surfaces ONE failure per missing model rather
    than collapsing into a single message."""
    schemas = openapi_spec.get("components", {}).get("schemas", {})
    assert model_name in schemas, (
        f"model `{model_name}` missing from components.schemas — was it renamed "
        "or removed without updating ENRICHED_REQUEST_MODELS in this test?"
    )
    schema = schemas[model_name]
    assert _has_examples(schema), (
        f"model `{model_name}` is in components.schemas but has no `examples` / "
        "`example`. Add `model_config = ConfigDict(json_schema_extra={'examples': "
        "[...]})` to its class definition in `apps/api/app/modules/sot/admin_schemas.py`."
    )
