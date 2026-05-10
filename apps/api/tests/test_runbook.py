"""Story 4.2 — `/agent-runbook` route contract tests.

Asserts the route returns 200 + `text/markdown; charset=utf-8` when the
runbook file exists, and 503 with a deploy-bug detail when it doesn't.
Also confirms the route is mounted at root (NOT under /api/) and is
unauthenticated (no cookie/header required).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.runbook import router as runbook_module


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """TestClient with the runbook source path pointed at a tmpdir file we
    control. Avoids the production /app/static/agent-runbook.md path."""
    fake_runbook = tmp_path / "agent-runbook.md"
    fake_runbook.write_text(
        "# Test runbook\n\nA short runbook used by tests.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runbook_module, "RUNBOOK_PATH", fake_runbook)
    app = create_app()
    with TestClient(app) as c:
        yield c, fake_runbook


def test_get_returns_200_with_markdown_content_type(client):
    c, _ = client
    resp = c.get("/agent-runbook")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/markdown; charset=utf-8"
    assert resp.text.startswith("# Test runbook")


def test_get_does_not_require_auth(client):
    """No login flow, no cookies, no CSRF header — public read per Decision B."""
    c, _ = client
    resp = c.get("/agent-runbook")
    assert resp.status_code == 200
    # If auth were required, the unauthenticated TestClient call would 401/403
    # rather than returning the body content.


def test_route_is_root_level_not_under_api(client):
    """Decision A: /agent-runbook is a top-level discovery resource, NOT
    /api/agent-runbook. Hitting /api/agent-runbook should 404."""
    c, _ = client
    resp = c.get("/api/agent-runbook")
    assert resp.status_code == 404


def test_returns_503_when_runbook_file_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Deploy-bug surface: missing /app/static/agent-runbook.md surfaces as
    503 Service Unavailable, not silent 404 (which would suggest the route
    is unreachable)."""
    missing = tmp_path / "does-not-exist.md"
    monkeypatch.setattr(runbook_module, "RUNBOOK_PATH", missing)
    app = create_app()
    with TestClient(app) as c:
        resp = c.get("/agent-runbook")
    assert resp.status_code == 503
    detail = resp.json().get("detail", "")
    assert "not found" in detail.lower() or "missing" in detail.lower()


def test_route_in_openapi_with_summary_and_description():
    """The route should surface in OpenAPI with summary + description set
    (parallels the Story 4.3 enrichment pattern). Uses app.openapi() direct
    to avoid running the lifespan."""
    spec = create_app().openapi()
    op = spec["paths"]["/agent-runbook"]["get"]
    assert op.get("summary"), "missing summary on GET /agent-runbook"
    assert op.get("description"), "missing description on GET /agent-runbook"
    assert op.get("tags") == ["agent-runbook"]
