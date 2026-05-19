"""TOTP 2FA enrollment + verify router — four endpoints under /api/auth/2fa/*.

* ``POST /api/auth/2fa/enroll`` — mint secret + QR + Redis-stashed token.
* ``POST /api/auth/2fa/enroll/confirm`` — verify code, persist Fernet-encrypted
  secret, mint 8 recovery codes, emit ``auth.totp.enrolled`` audit row.
* ``GET /api/auth/2fa/status`` — return enrollment + active-batch metadata.
* ``POST /api/auth/2fa/verify`` — Story 7.3 partial-auth → full-auth exchange
  (TOTP code OR recovery code; sets session cookies; emits
  ``auth.totp.verify.{success,fail}`` + ``auth.recovery_code.used``).

Audit emission lives in this module so the service stays a pure
encryption-and-persistence boundary (Decision D §1509). The Fernet-key gate
is re-tightened here via ``_assert_fernet_key_configured`` because the
Settings validator was relaxed to warn-only in Story 7.1 commit 2266721.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import re
import uuid
from typing import Annotated

import bcrypt
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import update
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.cookies import set_session_cookies
from app.core.auth.dependencies import current_user
from app.core.auth.jwt import encode_token
from app.core.auth.refresh import new_refresh_row
from app.core.config import Settings, get_settings
from app.core.db.models import RecoveryCode, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine, get_session
from app.modules.auth.models import LoginResponse, MeResponse
from app.modules.auth.router import client_meta
from app.modules.auth.totp.schemas import (
    ConfirmRequest,
    ConfirmResponse,
    EnrollResponse,
    StatusResponse,
    VerifyRequest,
)
from app.modules.auth.totp.service import (
    EnrollmentTokenInvalid,
    EnrollmentTokenUserMismatch,
    InvalidTotpCode,
    Settings2faService,
    _assert_fernet_key_configured,
    decrypt_secret,
    verify_totp_code,
)

_PARTIAL_KEY_PREFIX = "totp:partial:"
_TOTP_CODE_REGEX = re.compile(r"^\d{6}$")

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


@router.post(
    "/2fa/verify",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify second factor — TOTP or recovery code — and issue cookies",
    description=(
        "Exchange a partial_token (issued by POST /api/auth/login for "
        "users with totp_enabled_at IS NOT NULL) plus either a 6-digit "
        "TOTP code OR an 8-char hex recovery code for a fully "
        "authenticated session. On success: issues portal_access + "
        "portal_refresh cookies, creates a new RefreshToken family row, "
        "consumes the partial_token, emits auth.totp.verify.success "
        "and (if recovery_code) auth.recovery_code.used audit rows."
    ),
)
async def verify_second_factor(
    payload: VerifyRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    redis = request.app.state.redis.get()
    request_id = request.headers.get("x-request-id")
    partial_key = f"{_PARTIAL_KEY_PREFIX}{payload.partial_token}"

    # Step 1 — read the Redis stash. Miss / expired → 401, no audit
    # emission (no safe user_id attribution).
    raw = await redis.get(partial_key)
    if raw is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "partial_token_invalid")
    try:
        stash = json.loads(raw)
        stash_user_id = uuid.UUID(stash["user_id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "partial_token_invalid") from exc

    # Step 2 — load user and re-verify TOTP-enabled invariant.
    user = session.get(User, stash_user_id)
    if user is None or user.totp_enabled_at is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "partial_token_invalid")

    # Step 3 — defense-in-depth against impossible-by-Story-7.2 state.
    if user.totp_secret is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "totp_corrupt_state")

    # Step 4 — branch by code shape. Pydantic regex guarantees the input
    # matches ``^(\d{6}|[0-9a-f]{8})$`` so the negative branch is the
    # recovery-code path by elimination.
    is_totp_path = _TOTP_CODE_REGEX.fullmatch(payload.code) is not None
    matched_row: RecoveryCode | None = None
    method: str

    if is_totp_path:
        method = "totp"
        try:
            secret = decrypt_secret(user.totp_secret, settings)
        except InvalidToken:
            record_event(
                get_engine(),
                action="auth.totp.verify.fail",
                entity_type="user",
                entity_id=user.id,
                actor_user_id=user.id,
                after={"method": "totp", "reason": "fernet_invalid_token"},
                request_id=request_id,
            )
            raise HTTPException(  # noqa: B904 — explicit 401, original cause not actionable
                status.HTTP_401_UNAUTHORIZED, "invalid_code"
            )
        if not verify_totp_code(secret, payload.code):
            record_event(
                get_engine(),
                action="auth.totp.verify.fail",
                entity_type="user",
                entity_id=user.id,
                actor_user_id=user.id,
                after={"method": "totp"},
                request_id=request_id,
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_code")
    else:
        method = "recovery_code"

        # Story 7.3 Codex P2-3: bcrypt.checkpw at cost 12 blocks the event
        # loop ~200ms per candidate row; an 8-code batch can stall the
        # worker for >1.5s. Off-load the SELECT + the per-row checkpw loop
        # to a threadpool worker (sync SQLModel session is safe here —
        # ``check_same_thread=False`` for SQLite, and the caller awaits
        # exclusively so the Session is single-threaded-at-a-time).
        def _match_recovery_row() -> RecoveryCode | None:
            rows = list(
                session.exec(
                    select(RecoveryCode)
                    .where(RecoveryCode.user_id == user.id)
                    .where(RecoveryCode.invalidated_at.is_(None))
                    .where(RecoveryCode.used_at.is_(None))
                    .order_by(RecoveryCode.generated_at.desc())
                ).all()
            )
            for row in rows:
                if bcrypt.checkpw(payload.code.encode(), row.code_hash.encode()):
                    return row
            return None

        matched_row = await asyncio.to_thread(_match_recovery_row)
        if matched_row is None:
            record_event(
                get_engine(),
                action="auth.totp.verify.fail",
                entity_type="user",
                entity_id=user.id,
                actor_user_id=user.id,
                after={"method": "recovery_code"},
                request_id=request_id,
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_code")

    # Story 7.3 Codex P2-2: atomic Redis GETDEL claim AFTER code verify.
    # Mirrors the Story 7.2 enrollment-confirm pattern — read-then-delete
    # on Step 1 + final ``delete`` would let two concurrent /verify on the
    # same partial_token both pass the read and double-mint refresh
    # families. GETDEL is a single indivisible op under Redis's
    # single-threaded model; the loser sees ``None`` and gets a clean 401.
    # Placed after code verify so invalid-code paths leave the token
    # in place for retry (matches the prior Step-8-delete behaviour).
    claimed = await redis.execute_command("GETDEL", partial_key)
    if claimed is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "partial_token_invalid")

    used_at_value: datetime.datetime | None = None
    if matched_row is not None:
        # Story 7.3 Codex P2-4: conditional UPDATE with ``used_at IS NULL``
        # in the WHERE clause — the race-narrow consumption check now
        # lives in the DB, not in Python. Two concurrent /verify calls on
        # DIFFERENT partial_tokens (P2-2 cannot help here — they're
        # separate keys) but the SAME recovery code can both pass the
        # bcrypt match; only one wins this UPDATE (rowcount == 1). The
        # loser surfaces 401 invalid_code; their partial_token was already
        # GETDEL-claimed so re-login is required (acceptable rarity).
        used_at_value = datetime.datetime.now(datetime.UTC)
        result = session.execute(
            update(RecoveryCode)
            .where(RecoveryCode.id == matched_row.id)
            .where(RecoveryCode.used_at.is_(None))
            .values(used_at=used_at_value)
        )
        if result.rowcount == 0:
            session.rollback()
            record_event(
                get_engine(),
                action="auth.totp.verify.fail",
                entity_type="user",
                entity_id=user.id,
                actor_user_id=user.id,
                after={"method": "recovery_code", "reason": "already_consumed"},
                request_id=request_id,
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_code")

    # Step 6 — mint refresh-token family + access token (both paths).
    ip, ua = client_meta(request)
    refresh_secret, refresh_row = new_refresh_row(
        user_id=user.id,
        family_id=None,
        family_issued_at=None,
        ip=ip,
        user_agent=ua,
    )
    session.add(refresh_row)

    # Step 7 — atomic commit covering the RefreshToken INSERT and the
    # recovery_codes.used_at UPDATE (recovery-code path only).
    session.commit()

    if matched_row is not None:
        record_event(
            get_engine(),
            action="auth.recovery_code.used",
            entity_type="recovery_code",
            entity_id=matched_row.id,
            actor_user_id=user.id,
            after={
                "batch_id": str(matched_row.batch_id),
                "used_at": used_at_value.isoformat() if used_at_value else "",
            },
            request_id=request_id,
        )
    record_event(
        get_engine(),
        action="auth.totp.verify.success",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        after={"method": method},
        request_id=request_id,
    )

    # Step 8 — issue cookies and return LoginResponse. Partial_token was
    # already consumed by the GETDEL claim above; no further Redis op.
    access = encode_token(
        subject=str(user.id),
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    set_session_cookies(response, access=access, refresh=refresh_secret, settings=settings)

    return LoginResponse(
        partial_auth=False,
        user=MeResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value,
        ),
    )
