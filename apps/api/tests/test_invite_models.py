"""Unit tests for invite-token primitives (AC-2).

Covers `InviteTTLPreset` enum membership/values, `hash_token` determinism,
and `InviteToken` SQLModel column ergonomics against the live test SQLite.
"""

from __future__ import annotations

import datetime
import uuid

from sqlmodel import Session, select

from app.core.db.models import User, UserRole
from app.core.db.session import get_engine
from app.modules.invite.models import InviteToken, InviteTTLPreset, hash_token


def test_invite_ttl_preset_members_and_values() -> None:
    assert InviteTTLPreset.ONE_DAY.value == 86400
    assert InviteTTLPreset.THREE_DAYS.value == 259200
    assert InviteTTLPreset.SEVEN_DAYS.value == 604800
    assert InviteTTLPreset.THIRTY_DAYS.value == 2592000
    assert {p.name for p in InviteTTLPreset} == {
        "ONE_DAY",
        "THREE_DAYS",
        "SEVEN_DAYS",
        "THIRTY_DAYS",
    }


def test_hash_token_is_deterministic_sha256_hex() -> None:
    digest = hash_token("test")
    assert digest == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    assert len(digest) == 64
    assert digest == hash_token("test")


def test_invite_token_can_be_inserted_and_queried() -> None:
    engine = get_engine()
    admin_id: uuid.UUID
    with Session(engine) as session:
        admin = User(
            email=f"admin-{uuid.uuid4().hex[:8]}@example.invalid",
            display_name="Admin",
            role=UserRole.admin,
            password_hash="x",
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        admin_id = admin.id

        invite = InviteToken(
            token_hash=hash_token(f"token-{uuid.uuid4()}"),
            role=UserRole.member.value,
            generated_by_user_id=admin_id,
            ttl_seconds=InviteTTLPreset.SEVEN_DAYS.value,
        )
        session.add(invite)
        session.commit()
        session.refresh(invite)
        invite_id = invite.id

    with Session(engine) as session:
        fetched = session.exec(select(InviteToken).where(InviteToken.id == invite_id)).one()

    assert fetched.role == "member"
    assert fetched.ttl_seconds == InviteTTLPreset.SEVEN_DAYS.value
    assert fetched.generated_by_user_id == admin_id
    assert fetched.used_by_user_id is None
    assert fetched.used_at is None
    assert fetched.revoked_at is None
    assert fetched.generated_at.tzinfo is not None
    assert fetched.generated_at <= datetime.datetime.now(datetime.UTC)


def test_invite_token_hash_unique_constraint() -> None:
    """Two rows with the same token_hash must be rejected by the UNIQUE index."""
    engine = get_engine()
    shared_hash = hash_token(f"shared-{uuid.uuid4()}")
    with Session(engine) as session:
        first = InviteToken(
            token_hash=shared_hash,
            role=UserRole.member.value,
            ttl_seconds=InviteTTLPreset.ONE_DAY.value,
        )
        session.add(first)
        session.commit()

    with Session(engine) as session:
        dup = InviteToken(
            token_hash=shared_hash,
            role=UserRole.member.value,
            ttl_seconds=InviteTTLPreset.ONE_DAY.value,
        )
        session.add(dup)
        try:
            session.commit()
        except Exception:
            session.rollback()
        else:
            raise AssertionError("UNIQUE constraint did not fire on duplicate token_hash")
