"""TOTP 2FA service — the single cleartext-surface for Decision D §1509.

Cleartext ``totp_secret`` exists in process memory ONLY inside this module
for the duration of one enroll/verify call. Stored column values are always
Fernet ciphertext; the encryption helpers never log cleartext; and the
response serializers in ``apps/api/app/modules/auth/totp/schemas.py`` do
not expose the column at all.

Decision E §1515-1534 owns the recovery-codes batch generator: 8 codes per
batch, ``secrets.token_hex(4)`` per code (32 bits entropy), bcrypt cost 12
matching the existing ``app/core/auth/password.py`` precedent.
"""

from __future__ import annotations

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

from app.core.config import Settings
from app.core.db.models import RecoveryCode, User
from app.core.db.models._enums import UserRole

_KEY_PREFIX = "totp:enroll:"
_LOCK_PREFIX = "totp:confirm-lock:"
_ENROLLMENT_TTL_SECONDS = 600  # 10 minutes (epics.md §1676)
# The Dockerfile runs ``uvicorn --workers 2``; two concurrent /confirm hits
# on the same enrollment_token can otherwise both pass the GET-then-commit
# path and double-mint recovery batches (Story 7.2 Codex P2 race). A short
# SETNX lock keyed by enrollment_token serializes the critical section
# without breaking retry-on-invalid-code (the lock is released in finally
# regardless of outcome, while the enrollment-secret redis key only gets
# deleted on a successful commit). 30s ceiling covers worst-case 8-code
# bcrypt cost-12 hashing on slow hosts.
_LOCK_TTL_SECONDS = 30
_ISSUER_NAME = "3d-portal"
_RECOVERY_BATCH_SIZE = 8
_BCRYPT_ROUNDS = 12


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
    entropy → 8-char lowercase hex). Bcrypt cost 12 matches the
    ``hash_password`` precedent + Decision E §1524.
    """
    batch_id = uuid.uuid4()
    pairs: list[tuple[str, str]] = []
    for _ in range(_RECOVERY_BATCH_SIZE):
        cleartext = secrets.token_hex(4)
        digest = bcrypt.hashpw(
            cleartext.encode(),
            bcrypt.gensalt(rounds=_BCRYPT_ROUNDS),
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


class ConcurrentEnrollmentInProgress(Exception):
    """Another /confirm call is already running for this enrollment_token.

    Raised when the SETNX lock guarding the confirm critical section is
    already held — typically a second uvicorn worker handling a duplicate
    /confirm submission on the same enrollment_token. The loser must not
    advance state; the winner's commit is authoritative.
    """


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
        lock_key = f"{_LOCK_PREFIX}{enrollment_token}"

        # SETNX claim — only the winner enters the verify+commit critical
        # section. Held briefly (TTL ceiling) and released in finally so a
        # 422 (invalid code) still lets the user retry with the same token.
        acquired = await self._redis.set(
            lock_key,
            b"1",
            nx=True,
            ex=_LOCK_TTL_SECONDS,
        )
        if not acquired:
            raise ConcurrentEnrollmentInProgress

        try:
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

            await self._redis.delete(key)

            return _ConfirmPayload(
                recovery_codes=[cleartext for cleartext, _h in code_pairs],
                batch_id=batch_id,
                generated_at=now,
            )
        finally:
            await self._redis.delete(lock_key)

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
