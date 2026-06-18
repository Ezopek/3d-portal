"""TOTP 2FA service — the single cleartext-surface for Decision D §1509.

Cleartext ``totp_secret`` exists in process memory ONLY inside this module
for the duration of one enroll/verify call. Stored column values are always
Fernet ciphertext; the encryption helpers never log cleartext; and the
response serializers in ``apps/api/app/modules/auth/totp/schemas.py`` do
not expose the column at all.

Decision E §1515-1534 owns the recovery-codes batch generator: 8 codes per
batch, ``secrets.token_hex(4)`` per code (32 bits entropy), bcrypt cost 12 in
production matching the existing ``app/core/auth/password.py`` precedent.
"""

from __future__ import annotations

import contextlib
import datetime
import io
import json
import secrets
import uuid
from dataclasses import dataclass

import bcrypt
import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.core.db.models import RecoveryCode, User
from app.core.db.models._enums import UserRole

_KEY_PREFIX = "totp:enroll:"
_ENROLLMENT_TTL_SECONDS = 600  # 10 minutes (epics.md §1676)
# Story 7.2 Codex P2 race: ``uvicorn --workers 2`` means two concurrent
# /confirm calls on the same enrollment_token can both pass code verify
# before either deletes the redis key, double-minting recovery batches.
# Resolved via atomic Redis GETDEL claim AFTER code verify (single-op
# read+delete, indivisible under Redis single-threaded model). Replaces
# the earlier SETNX-lock-with-TTL pattern which could race under slow-
# commit if the lock TTL expired mid-critical-section.
_ISSUER_NAME = "3d-portal"
_RECOVERY_BATCH_SIZE = 8


# ---------------------------------------------------------------------------
# Pure helpers — the single cleartext surface
# ---------------------------------------------------------------------------


def _assert_fernet_key_configured(settings: Settings) -> None:
    """Hard-fail at endpoint-init when the Fernet key is unset.

    Story 7.1's production-incident-relax (commit 2266721) loosened the
    Settings validator from raise-on-empty-prod to warn-on-empty-prod;
    this guard re-tightens the gate at the path where the key is actually
    load-bearing so a misconfigured deployment surfaces a clean 500
    instead of an obscure cryptography.fernet error.
    """
    if not settings.totp_fernet_key:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "totp_not_configured",
        )


def generate_totp_secret() -> str:
    """Return a fresh ``pyotp.random_base32()`` secret (32-char base32)."""
    return pyotp.random_base32()


def build_provisioning_uri(secret: str, account_email: str) -> str:
    """Return the otpauth:// URI per RFC 6238 issuer/account convention."""
    return pyotp.TOTP(secret).provisioning_uri(
        name=account_email,
        issuer_name=_ISSUER_NAME,
    )


def render_qr_svg(provisioning_uri: str) -> str:
    """Render the provisioning URI as a compact path-based SVG string."""
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(provisioning_uri, image_factory=factory)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


def verify_totp_code(secret: str, code: str) -> bool:
    """Return True when the code matches secret within ±30s drift."""
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def encrypt_secret(cleartext: str, settings: Settings) -> str:
    """Fernet-encrypt the cleartext secret; return the ciphertext str."""
    return Fernet(settings.totp_fernet_key.encode()).encrypt(cleartext.encode()).decode()


def decrypt_secret(ciphertext: str, settings: Settings) -> str:
    """Fernet-decrypt the stored ciphertext; return the cleartext.

    The only function in the codebase that touches cleartext TOTP secrets
    stored in the user table (Decision D §1509). Story 7.2 uses this only
    in the round-trip test; Story 7.3's partial-auth verify handler will
    call it from the login flow.
    """
    return Fernet(settings.totp_fernet_key.encode()).decrypt(ciphertext.encode()).decode()


def generate_recovery_codes_batch() -> tuple[uuid.UUID, list[tuple[str, str]]]:
    """Mint a fresh 8-code batch + its bcrypt digests.

    Returns ``(batch_id, [(cleartext, bcrypt_hash), ...])`` with one entry
    per code. Decision E §1530 binds ``secrets.token_hex(4)`` (32 bits of
    entropy → 8-char lowercase hex). Production bcrypt cost 12 matches the
    ``hash_password`` precedent + Decision E §1524; tests may lower it via
    settings to keep the full suite deterministic and bounded.
    """
    batch_id = uuid.uuid4()
    pairs: list[tuple[str, str]] = []
    for _ in range(_RECOVERY_BATCH_SIZE):
        cleartext = secrets.token_hex(4)
        digest = bcrypt.hashpw(
            cleartext.encode(),
            bcrypt.gensalt(rounds=get_settings().bcrypt_rounds),
        ).decode()
        pairs.append((cleartext, digest))
    return batch_id, pairs


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _EnrollPayload:
    qr_svg: str
    manual_secret: str
    enrollment_token: str


@dataclass(frozen=True)
class _ConfirmPayload:
    recovery_codes: list[str]
    batch_id: uuid.UUID
    generated_at: datetime.datetime


@dataclass(frozen=True)
class _StatusPayload:
    enabled: bool
    batch_id: uuid.UUID | None
    generated_at: datetime.datetime | None
    codes_remaining: int | None


class EnrollmentTokenInvalid(Exception):
    """Redis stash miss / TTL expired."""


class EnrollmentTokenUserMismatch(Exception):
    """The current user does not own the enrollment_token's user_id."""


class InvalidTotpCode(Exception):
    """pyotp.verify returned False."""


class Settings2faService:
    """Owns the encryption boundary + the enroll-confirm DB transaction."""

    def __init__(self, *, redis: Redis, engine: Engine, settings: Settings) -> None:
        self._redis = redis
        self._engine = engine
        self._settings = settings

    async def begin_enrollment(self, *, user_id: uuid.UUID, account_email: str) -> _EnrollPayload:
        """Mint secret + QR + enrollment_token; Redis SETEX 600s."""
        secret = generate_totp_secret()
        uri = build_provisioning_uri(secret, account_email)
        qr_svg = render_qr_svg(uri)
        enrollment_token = secrets.token_urlsafe(32)
        payload = json.dumps({"user_id": str(user_id), "secret": secret})
        await self._redis.set(
            f"{_KEY_PREFIX}{enrollment_token}",
            payload.encode(),
            ex=_ENROLLMENT_TTL_SECONDS,
        )
        return _EnrollPayload(
            qr_svg=qr_svg,
            manual_secret=secret,
            enrollment_token=enrollment_token,
        )

    async def confirm_enrollment(
        self,
        *,
        enrollment_token: str,
        code: str,
        current_user_id: uuid.UUID,
    ) -> _ConfirmPayload:
        """Verify code, persist Fernet ciphertext, mint 8 recovery codes."""
        key = f"{_KEY_PREFIX}{enrollment_token}"

        # Step 1: read pending payload for code verification (no consumption
        # yet — bad-code paths must let the user retry with the same token).
        raw = await self._redis.get(key)
        if raw is None:
            raise EnrollmentTokenInvalid
        payload = json.loads(raw)
        stash_user_id = uuid.UUID(payload["user_id"])
        if stash_user_id != current_user_id:
            raise EnrollmentTokenUserMismatch
        secret = payload["secret"]
        if not verify_totp_code(secret, code):
            raise InvalidTotpCode

        # Step 2: atomic claim — only at this point we know commit is going
        # to happen. Redis GETDEL is an indivisible operation; the second
        # concurrent confirm (across uvicorn workers) sees None and raises
        # EnrollmentTokenInvalid (no SETNX-lock TTL race possible because
        # the claim is atomic-by-design, not lock-protected).
        claimed = await self._redis.execute_command("GETDEL", key)
        if claimed is None:
            # Another worker passed verify and consumed the token between
            # our Step 1 read and this GETDEL — they will mint codes.
            raise EnrollmentTokenInvalid

        # Step 3: persistence path — wrap in try/except so a DB stall,
        # encryption failure, or worker termination after the GETDEL claim
        # restores the token to Redis (best-effort) and lets the user
        # retry. The restore is non-atomic vs. a parallel claim, but the
        # window is small (a fresh GETDEL is unlikely between failure +
        # restore) and the alternative (lost token + forced re-enroll)
        # is a strictly worse UX on transient errors.
        try:
            ciphertext = encrypt_secret(secret, self._settings)
            now = datetime.datetime.now(datetime.UTC)
            batch_id, code_pairs = generate_recovery_codes_batch()

            with Session(self._engine) as session:
                user = session.get(User, current_user_id)
                if user is None:
                    # Defense-in-depth — current_user JWT was valid but row gone.
                    raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
                user.totp_secret = ciphertext
                user.totp_enabled_at = now
                session.add(user)
                for _cleartext, code_hash in code_pairs:
                    session.add(
                        RecoveryCode(
                            user_id=user.id,
                            code_hash=code_hash,
                            batch_id=batch_id,
                            generated_at=now,
                        )
                    )
                session.commit()
        except Exception:
            # Best-effort restore so the user can retry on transient failure.
            # The TTL is approximate (we lose the elapsed-time delta since
            # the original SET) but tighter than expiring forever.
            with contextlib.suppress(Exception):
                await self._redis.set(
                    key,
                    claimed,
                    ex=_ENROLLMENT_TTL_SECONDS,
                )
            raise

        return _ConfirmPayload(
            recovery_codes=[cleartext for cleartext, _h in code_pairs],
            batch_id=batch_id,
            generated_at=now,
        )

    def read_status(self, *, user_id: uuid.UUID) -> _StatusPayload:
        """Synchronous read of users.totp_enabled_at + active batch."""
        with Session(self._engine) as session:
            user = session.get(User, user_id)
            if user is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
            if user.role == UserRole.agent:
                return _StatusPayload(
                    enabled=False,
                    batch_id=None,
                    generated_at=None,
                    codes_remaining=None,
                )
            if user.totp_enabled_at is None:
                return _StatusPayload(
                    enabled=False,
                    batch_id=None,
                    generated_at=None,
                    codes_remaining=None,
                )
            leader = session.exec(
                select(RecoveryCode)
                .where(RecoveryCode.user_id == user.id)
                .where(RecoveryCode.invalidated_at.is_(None))
                .order_by(RecoveryCode.generated_at.desc())
                .limit(1)
            ).first()
            if leader is None:
                return _StatusPayload(
                    enabled=True,
                    batch_id=None,
                    generated_at=None,
                    codes_remaining=0,
                )
            remaining_rows = session.exec(
                select(RecoveryCode)
                .where(RecoveryCode.user_id == user.id)
                .where(RecoveryCode.batch_id == leader.batch_id)
                .where(RecoveryCode.used_at.is_(None))
                .where(RecoveryCode.invalidated_at.is_(None))
            ).all()
            return _StatusPayload(
                enabled=True,
                batch_id=leader.batch_id,
                generated_at=leader.generated_at,
                codes_remaining=len(remaining_rows),
            )
