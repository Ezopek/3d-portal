"""Public-side ``POST /api/auth/password-reset`` consume endpoint (Story 8.5).

Atomic single-use claim → password validation → user lookup → password
update → audit emission. NO cookies issued — the user must subsequently
``POST /api/auth/login`` with the new password. Public endpoint (no
``current_user`` dependency).

Failure-path reasons emitted on ``auth.password.reset.completed``:
- ``token_invalid``   — Redis miss post-GETDEL (never existed / expired /
                        already claimed; uniform-error per Story 6.4 convention).
- ``weak_password``   — length<12 OR zxcvbn score<3 (user identity is known
                        post-claim, so entity_id IS set on this emission).
- ``user_not_found``  — target row deleted between mint and consume.

The success-path emission uses ``actor_user_id == entity_id == target.id`` —
the user resetting their own password is both actor AND entity (the
self-action discriminator).
"""

from __future__ import annotations

import uuid
from typing import Annotated

import zxcvbn
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.core.audit import record_event
from app.core.auth.password import hash_password
from app.core.db.models import User
from app.core.db.session import get_engine, get_session
from app.modules.auth.password_reset.schemas import PasswordResetConsumeRequest
from app.modules.auth.password_reset.service import PasswordResetService

# Re-use the Story 6.4 register-endpoint password-policy constants verbatim.
# The policy (≥12 chars + zxcvbn ≥3) is a stable PRD contract; if the
# cross-module private-name import surfaces as a lint objection during
# review, promote to ``apps/api/app/core/auth/password_policy.py`` as a
# 4-line public module — DEFER until raised.
from app.modules.invite.router import (
    _LEN_MSG,
    _MIN_PASSWORD_LEN,
    _MIN_ZXCVBN_SCORE,
    _SCORE_MSG,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _service(request: Request) -> PasswordResetService:
    return PasswordResetService(redis=request.app.state.redis.get())


@router.post(
    "/password-reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Consume a single-use admin-issued password-reset link",
    description=(
        "Public endpoint (no auth cookies required). Atomically claims the "
        "Redis-stored token via GETDEL, validates the new password against the "
        "Story 6.4 register-endpoint policy (≥12 chars + zxcvbn ≥3), updates "
        "``users.password_hash`` via the project's bcrypt cost-12 helper, and "
        "emits ``auth.password.reset.completed`` audit. Returns 204 (NO cookies "
        "issued — this endpoint is NOT a login surface; the user must "
        "subsequently POST /api/auth/login with the new password). Returns 404 "
        "``token_invalid`` uniformly for never-existed / expired / "
        "already-consumed token states (Redis-only state cannot distinguish "
        "them post-GETDEL — deliberate token-status-enumeration protection per "
        "Story 6.4 convention). Returns 422 ``weak_password`` for "
        "policy-failing passwords. Returns 404 ``user_not_found`` if the target "
        "row was deleted between mint and consume. Refresh-token families are "
        "NOT proactively invalidated (Decision I §1622 binds force-logout to "
        "the Story 8.3 admin actions, NOT to password rotation)."
    ),
)
async def consume_password_reset(
    payload: PasswordResetConsumeRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    engine = get_engine()
    request_id = request.headers.get("x-request-id")
    service = _service(request)

    # Codex P2 fix-up: validate password BEFORE the destructive GETDEL claim.
    # Otherwise a weak-password attempt burns the only token + inline-422
    # UI promises retryability that the server can't honor.
    if len(payload.new_password) < _MIN_PASSWORD_LEN:
        record_event(
            engine,
            action="auth.password.reset.completed",
            entity_type="user",
            entity_id=None,
            actor_user_id=None,
            after={"reason": "weak_password"},
            request_id=request_id,
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, _LEN_MSG)
    score = zxcvbn.zxcvbn(payload.new_password)["score"]
    if score < _MIN_ZXCVBN_SCORE:
        record_event(
            engine,
            action="auth.password.reset.completed",
            entity_type="user",
            entity_id=None,
            actor_user_id=None,
            after={"reason": "weak_password"},
            request_id=request_id,
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, _SCORE_MSG)

    # Step 1 — atomic token claim. Loser of any GETDEL race observes None.
    # Password is already validated above; this consume-and-act is one-shot.
    user_id: uuid.UUID | None = await service.claim(payload.token)
    if user_id is None:
        record_event(
            engine,
            action="auth.password.reset.completed",
            entity_type="user",
            entity_id=None,
            actor_user_id=None,
            after={"reason": "token_invalid"},
            request_id=request_id,
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "token_invalid")

    # Step 3 — user lookup. The row may have been deleted between mint
    # and consume; surface as 404 with a distinct audit reason.
    target = session.get(User, user_id)
    if target is None:
        record_event(
            engine,
            action="auth.password.reset.completed",
            entity_type="user",
            entity_id=user_id,
            actor_user_id=None,
            after={"reason": "user_not_found"},
            request_id=request_id,
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")

    # Step 4 — password update.
    target.password_hash = hash_password(payload.new_password)
    session.add(target)
    session.commit()

    # Step 5 — success audit (actor == entity == target.id).
    record_event(
        engine,
        action="auth.password.reset.completed",
        entity_type="user",
        entity_id=target.id,
        actor_user_id=target.id,
        after={"email": target.email},
        request_id=request_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
