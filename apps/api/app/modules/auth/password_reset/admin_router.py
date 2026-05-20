"""Admin-side ``POST /api/admin/users/{user_id}/password-reset`` (Story 8.5).

Mints a single-use Redis-backed password-reset link and emits the
``auth.password.reset.initiated`` audit event with the actor-pivot
discriminator (``actor_user_id = admin_id != entity_id = target.id``).
Three foot-gun guards mirror Stories 8.3 + 8.4 verbatim:
  - ``cannot_target_self`` — Decision L §1741 (self-reset via DB-direct on
    .190 until self-hosted mail arrives).
  - ``cannot_target_agent`` — NFR5-INT-1 (agent password is
    bootstrap-script-managed).
  - ``user_not_found`` — standard 404.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.config import Settings, get_settings
from app.core.db.models import User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine, get_session
from app.modules.auth.password_reset.schemas import PasswordResetMintResponse
from app.modules.auth.password_reset.service import PasswordResetService

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _service(request: Request) -> PasswordResetService:
    return PasswordResetService(redis=request.app.state.redis.get())


@router.post(
    "/users/{user_id}/password-reset",
    response_model=PasswordResetMintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a single-use password-reset link for a user (admin only)",
    description=(
        "Mints a Redis-backed single-use opaque token for the target user and "
        "returns the cleartext ``reset_url`` ONCE — subsequent admin-panel reads "
        "cannot retrieve it (Redis is the sole holder, no list endpoint exists for "
        "password-reset tokens). The operator delivers the link out-of-band "
        "(SMS, Messenger, personal mail) per Decision L §1741 until the self-hosted "
        "mail server initiative ships. Two foot-gun guards mirror Stories 8.3 + 8.4: "
        "**cannot_target_self** 400 (the operator's own password is rotated via "
        "DB-direct surgery on .190 per Decision L §1741 — issuing via this endpoint "
        "would create a paper-trail anomaly that contradicts FR5-AUDIT-1's "
        "actor!=target invariant); **cannot_target_agent** 400 (NFR5-INT-1 — the "
        "agent service account password is bootstrap-script-managed). Emits "
        "``auth.password.reset.initiated`` audit with ``actor_user_id != entity_id`` "
        "AND ``after.ttl_seconds`` — that payload shape discriminates this admin-side "
        "emission from the public-consume ``auth.password.reset.completed`` emission "
        "(actor == entity). This is Step 2 of the lost-2FA-AND-lost-recovery-codes "
        "recovery flow (epics §1817); Step 1 is the Story 8.4 force-disable-2FA "
        "endpoint. NO DB-row audit history is kept at the password-reset-link tier "
        "per epics §1814 — the two audit-log emissions ARE the audit history."
    ),
)
async def issue_password_reset_admin_user(
    user_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    admin_id: uuid.UUID = current_admin,
) -> PasswordResetMintResponse:
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    if target.id == admin_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_self")
    if target.role == UserRole.agent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_agent")

    service = _service(request)
    ttl_seconds = settings.password_reset_ttl_seconds
    token = await service.generate(
        user_id=target.id,
        generated_by_user_id=admin_id,
        ttl_seconds=ttl_seconds,
    )

    record_event(
        get_engine(),
        action="auth.password.reset.initiated",
        entity_type="user",
        entity_id=target.id,
        actor_user_id=admin_id,
        after={"ttl_seconds": ttl_seconds},
        request_id=request.headers.get("x-request-id"),
    )

    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=ttl_seconds)
    return PasswordResetMintResponse(
        reset_url=f"/reset-password?token={token}",
        expires_at=expires_at,
    )
