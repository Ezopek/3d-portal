"""TOTP 2FA enrollment router (Story 7.2) — three endpoints under /api/auth/2fa/*.

* ``POST /api/auth/2fa/enroll`` — mint secret + QR + Redis-stashed token.
* ``POST /api/auth/2fa/enroll/confirm`` — verify code, persist Fernet-encrypted
  secret, mint 8 recovery codes, emit ``auth.totp.enrolled`` audit row.
* ``GET /api/auth/2fa/status`` — return enrollment + active-batch metadata.

Audit emission lives in this module so the service stays a pure
encryption-and-persistence boundary (Decision D §1509). The Fernet-key gate
is re-tightened here via ``_assert_fernet_key_configured`` because the
Settings validator was relaxed to warn-only in Story 7.1 commit 2266721.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.audit import record_event
from app.core.auth.dependencies import current_user
from app.core.config import Settings, get_settings
from app.core.db.models import User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine, get_session
from app.modules.auth.totp.schemas import (
    ConfirmRequest,
    ConfirmResponse,
    EnrollResponse,
    StatusResponse,
)
from app.modules.auth.totp.service import (
    EnrollmentTokenInvalid,
    EnrollmentTokenUserMismatch,
    InvalidTotpCode,
    Settings2faService,
    _assert_fernet_key_configured,
)

router = APIRouter(prefix="/api/auth", tags=["auth", "2fa"])


def _service(request: Request, settings: Settings) -> Settings2faService:
    return Settings2faService(
        redis=request.app.state.redis.get(),
        engine=get_engine(),
        settings=settings,
    )


@router.post(
    "/2fa/enroll",
    response_model=EnrollResponse,
    status_code=status.HTTP_200_OK,
    summary="Begin TOTP enrollment — generate secret + QR + ephemeral token",
    description=(
        "Mint a fresh TOTP secret, render its provisioning URI as a QR-code "
        "SVG, and stash an enrollment token in Redis (TTL 600s) that the "
        "subsequent POST /2fa/enroll/confirm call exchanges for persistence. "
        "Forbidden for users with role=agent (FR5-2FA-3 — agents are service "
        "accounts; forcing 2FA would brick AI ingestion)."
    ),
)
async def begin_enrollment(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: uuid.UUID = current_user,
) -> EnrollResponse:
    _assert_fernet_key_configured(settings)
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    if user.role == UserRole.agent:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "agent_role_forbidden")
    if user.totp_enabled_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "totp_already_enrolled")

    service = _service(request, settings)
    result = await service.begin_enrollment(user_id=user.id, account_email=user.email)
    return EnrollResponse(
        qr_svg=result.qr_svg,
        manual_secret=result.manual_secret,
        enrollment_token=result.enrollment_token,
    )


@router.post(
    "/2fa/enroll/confirm",
    response_model=ConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm TOTP enrollment — verify code, persist secret, mint recovery codes",
    description=(
        "Exchange the enrollment_token + a fresh 6-digit TOTP code for "
        "persistent 2FA activation. On success: Fernet-encrypts the secret "
        "into users.totp_secret, sets users.totp_enabled_at = NOW(), mints "
        "8 single-use recovery codes (bcrypt-hashed at rest, shared batch_id), "
        "emits auth.totp.enrolled audit row, and returns the 8 cleartext "
        "codes ONCE in the response body. Subsequent reads cannot return "
        "cleartext."
    ),
)
async def confirm_enrollment(
    payload: ConfirmRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: uuid.UUID = current_user,
) -> ConfirmResponse:
    _assert_fernet_key_configured(settings)
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    if user.role == UserRole.agent:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "agent_role_forbidden")
    if user.totp_enabled_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "totp_already_enrolled")

    service = _service(request, settings)
    try:
        result = await service.confirm_enrollment(
            enrollment_token=payload.enrollment_token,
            code=payload.code,
            current_user_id=user.id,
        )
    except EnrollmentTokenInvalid as exc:
        # Note: also raised by the atomic GETDEL claim loser when a second
        # concurrent /confirm beats us between code-verify and consumption.
        # The race-winner's commit is authoritative; the loser must not
        # advance state. Same 404 surface as a genuinely expired/missing
        # token since user-visible recovery is identical (re-enroll).
        raise HTTPException(status.HTTP_404_NOT_FOUND, "enrollment_token_invalid") from exc
    except EnrollmentTokenUserMismatch as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "enrollment_token_user_mismatch") from exc
    except InvalidTotpCode as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_code") from exc

    record_event(
        get_engine(),
        action="auth.totp.enrolled",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        after={"batch_id": str(result.batch_id), "codes_count": 8},
        request_id=request.headers.get("x-request-id"),
    )

    return ConfirmResponse(
        recovery_codes=result.recovery_codes,
        batch_id=result.batch_id,
        generated_at=result.generated_at,
    )


@router.get(
    "/2fa/status",
    response_model=StatusResponse,
    summary="Read TOTP enrollment status + active recovery batch metadata",
    description=(
        "Returns whether the current user has TOTP enabled, and if so, the "
        "active recovery-codes batch metadata (batch_id, generated_at, "
        "codes_remaining). Cleartext codes + Fernet ciphertext are NEVER "
        "in the response. Agent role always sees enabled=false."
    ),
)
def read_status(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: uuid.UUID = current_user,
) -> StatusResponse:
    service = _service(request, settings)
    payload = service.read_status(user_id=user_id)
    return StatusResponse(
        enabled=payload.enabled,
        batch_id=payload.batch_id,
        generated_at=payload.generated_at,
        codes_remaining=payload.codes_remaining,
    )
