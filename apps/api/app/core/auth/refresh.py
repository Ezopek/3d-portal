"""apps/api/app/core/auth/refresh.py — refresh-token rotation helpers."""
from __future__ import annotations

import datetime
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from enum import Enum

from sqlmodel import Session, select

from app.core.db.models import RefreshToken

REFRESH_TTL_DAYS = 30
GRACE_SECONDS = 30


class RotationOutcome(str, Enum):
    rotated = "rotated"          # happy path
    grace_returned = "grace_returned"   # within 30 s, UA matched, returned active descendant
    grace_ua_mismatch = "grace_ua_mismatch"  # within 30 s but UA mismatch — denied without burn
    race_lost = "race_lost"      # within grace, no active descendant — benign race, nothing burned
    reuse_detected = "reuse_detected"   # outside grace (or non-rotated revoke), family burned
    not_found = "not_found"
    expired = "expired"


@dataclass
class RotationResult:
    outcome: RotationOutcome
    new_secret: str | None = None
    new_row: RefreshToken | None = None
    active_row: RefreshToken | None = None
    family_id: uuid.UUID | None = None


def generate_refresh_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def new_refresh_row(
    *,
    user_id: uuid.UUID,
    family_id: uuid.UUID | None,
    family_issued_at: datetime.datetime | None,
    ip: str | None,
    user_agent: str | None,
) -> tuple[str, RefreshToken]:
    """Create (but do not persist) a new refresh row + return its raw secret.

    Pass family_id=None to start a new family (login). For rotation, pass the
    parent's family_id and family_issued_at.
    """
    now = datetime.datetime.now(datetime.UTC)
    fam = family_id or uuid.uuid4()
    fam_issued = family_issued_at or now
    secret = generate_refresh_secret()
    row = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        family_id=fam,
        family_issued_at=fam_issued,
        token_hash=hash_refresh_secret(secret),
        issued_at=now,
        expires_at=now + datetime.timedelta(days=REFRESH_TTL_DAYS),
        last_used_at=now,
        ip=ip,
        user_agent=(user_agent or "")[:500] or None,
    )
    return secret, row


def find_by_secret(session: Session, secret: str) -> RefreshToken | None:
    h = hash_refresh_secret(secret)
    return session.exec(select(RefreshToken).where(RefreshToken.token_hash == h)).first()


def find_active_in_family(session: Session, family_id: uuid.UUID) -> RefreshToken | None:
    """Return the (single) active token in the family, or None if the family has no live descendant."""
    return session.exec(
        select(RefreshToken)
        .where(RefreshToken.family_id == family_id)
        .where(RefreshToken.revoked_at.is_(None))
    ).first()


def burn_family(session: Session, family_id: uuid.UUID) -> int:
    """Revoke every active row in the family with reason='reuse_detected'. Returns the number of rows revoked."""
    now = datetime.datetime.now(datetime.UTC)
    rows = session.exec(
        select(RefreshToken)
        .where(RefreshToken.family_id == family_id)
        .where(RefreshToken.revoked_at.is_(None))
    ).all()
    for r in rows:
        r.revoked_at = now
        r.revoke_reason = "reuse_detected"
        session.add(r)
    return len(rows)


def rotate_refresh(
    session: Session,
    *,
    presented: RefreshToken,
    ip: str | None,
    user_agent: str | None,
) -> RotationResult:
    """Execute the rotation algorithm. Caller commits."""
    now = datetime.datetime.now(datetime.UTC)
    if presented.expires_at < now:
        return RotationResult(outcome=RotationOutcome.expired, family_id=presented.family_id)

    if presented.revoked_at is not None:
        if (
            presented.revoke_reason == "rotated"
            and presented.replaced_at is not None
            and (now - presented.replaced_at).total_seconds() < GRACE_SECONDS
        ):
            active = find_active_in_family(session, presented.family_id)
            if active is None:
                return RotationResult(
                    outcome=RotationOutcome.race_lost, family_id=presented.family_id,
                )
            if (active.user_agent or "") != (user_agent or ""):
                return RotationResult(
                    outcome=RotationOutcome.grace_ua_mismatch,
                    family_id=presented.family_id,
                    active_row=active,
                )
            # Grace hit — return the existing active descendant unchanged.
            return RotationResult(
                outcome=RotationOutcome.grace_returned,
                active_row=active,
                family_id=presented.family_id,
            )
        # Reuse detected — outside grace OR not 'rotated' reason.
        burn_family(session, presented.family_id)
        return RotationResult(outcome=RotationOutcome.reuse_detected, family_id=presented.family_id)

    # Happy path — order matters because of ux_refresh_tokens_family_active.
    # Step 1: revoke the presented row WITHOUT replaced_by_id (no FK target yet).
    presented.revoked_at = now
    presented.revoke_reason = "rotated"
    presented.replaced_at = now
    session.add(presented)
    session.flush()  # release the partial-UNIQUE slot before INSERT

    # Step 2: insert the new row.
    new_secret, new_row = new_refresh_row(
        user_id=presented.user_id,
        family_id=presented.family_id,
        family_issued_at=presented.family_issued_at,
        ip=ip,
        user_agent=user_agent,
    )
    session.add(new_row)
    session.flush()

    # Step 3: backfill replaced_by_id on the old row.
    presented.replaced_by_id = new_row.id
    session.add(presented)

    return RotationResult(
        outcome=RotationOutcome.rotated,
        new_secret=new_secret,
        new_row=new_row,
        family_id=presented.family_id,
    )
