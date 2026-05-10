"""Self-serving agent runbook endpoint.

Exposes `GET /agent-runbook` as text/markdown. The runbook content lives at
`docs/agents-add-model-runbook.md` in source and is COPIED into the API
image at `/app/static/agent-runbook.md` by the Dockerfile (Story 4.2).

Public read — NO auth dependencies. The runbook documents how to
authenticate; gating it on auth would create a chicken-and-egg.

This router is mounted at root in `app.main:create_app` (NOT under the
`/api`-prefixed `api_router`) — `/agent-runbook` is conceptually a
top-level discovery resource, not part of the REST API surface.

Per Decision A + B + D in `_bmad-output/planning-artifacts/architecture.md`
§ Initiative 2.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["agent-runbook"])

# Deterministic on-image path. The Dockerfile COPYs
# `docs/agents-add-model-runbook.md` here so the runbook version-locks
# with the API deploy by image build.
RUNBOOK_PATH = Path("/app/static/agent-runbook.md")


@router.get(
    "/agent-runbook",
    response_class=PlainTextResponse,
    summary="Self-serving agent runbook (text/markdown, no auth)",
    description=(
        "Returns the canonical AI-agent runbook content as `text/markdown; charset=utf-8`. "
        "Public read — no auth, no CSRF gate. Bootstrap surface for fresh-session AI "
        "agents (Claude, Codex, future LLMs): one URL teaches principles, cookie-auth "
        "flow, source detection, Printables GraphQL recipe, 3MF conversion procedure, "
        "pre-flight checklist, OpenAPI cross-link, and behavioral side-effects. "
        "Companion to `/api/openapi.json` (endpoint catalog) per the layered "
        "auto-discovery contract (NFR8). Returns 503 if the runbook file is missing "
        "from the image — that signals a deploy bug, not a missing route, hence loud "
        "service-unavailable rather than silent 404. The fingerprint of the intro "
        "paragraph is checked by `infra/scripts/deploy.sh` post-deploy against "
        "`infra/.runbook-fingerprint`; mismatch yields a non-fatal warning."
    ),
    responses={
        200: {
            "description": "Runbook served as text/markdown",
            "content": {"text/markdown": {}},
        },
        503: {"description": "Runbook file missing from image (deploy bug)"},
    },
)
def get_runbook() -> PlainTextResponse:
    try:
        content = RUNBOOK_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "agent runbook not found in image — "
                f"expected at {RUNBOOK_PATH}. Deploy bug; check the COPY step in "
                "apps/api/Dockerfile."
            ),
        ) from exc
    return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")
