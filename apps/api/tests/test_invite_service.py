"""Tests for the Initiative 5 dual-backed invite-token service (Story 6.2)."""

from __future__ import annotations

import datetime
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db.models._enums import UserRole
from app.core.db.models._user import User
from app.core.db.session import get_engine
from app.modules.invite import (
    ActiveInvite,
    GenerateInviteResult,
    InviteAlreadyResolved,
    InviteConsumed,
    InviteNotFound,
    InviteService,
    InviteToken,
    hash_token,
)

_ADMIN = uuid.UUID("00000000-0000-0000-0000-0000000000ad")
_USER = uuid.UUID("00000000-0000-0000-0000-0000000000be")
_OTHER = uuid.UUID("00000000-0000-0000-0000-0000000000ce")


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis()


@pytest.fixture
def service(fake_redis):
    return InviteService(redis=fake_redis, engine=get_engine())


@pytest.fixture(autouse=True)
def _seed_users_and_clear_invites():
    """Seed FK-target user rows and wipe invite rows between tests.

    InviteToken.generated_by_user_id / used_by_user_id are real FKs to user.id
    (uuid_fk with ondelete=SET NULL). SQLite has foreign_keys=ON so the INSERT
    itself requires the referenced rows to exist.
    """
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(InviteToken)).all():
            s.delete(row)
        for uid, email in (
            (_ADMIN, "admin-invite-fix@example.test"),
            (_USER, "user-invite-fix@example.test"),
            (_OTHER, "other-invite-fix@example.test"),
        ):
            existing = s.get(User, uid)
            if existing is None:
                s.add(
                    User(
                        id=uid,
                        email=email,
                        display_name=email.split("@", 1)[0],
                        role=UserRole.admin if uid == _ADMIN else UserRole.member,
                        password_hash="$2b$12$fixture.placeholder.hash.value.fixed.0123456789012345",
                    )
                )
        s.commit()
    yield
    with Session(engine) as s:
        for row in s.exec(select(InviteToken)).all():
            s.delete(row)
        s.commit()


# ---------------------------------------------------------------------------
# generate_invite() — AC-1
# ---------------------------------------------------------------------------


async def test_generate_invite_writes_db_row_and_redis_key(service, fake_redis):
    result = await service.generate_invite(
        role=UserRole.member,
        ttl_seconds=86400,
        generated_by_user_id=_ADMIN,
    )

    assert isinstance(result, GenerateInviteResult)
    assert isinstance(result.token, str)
    assert len(result.token) == 43  # secrets.token_urlsafe(32) -> 43 chars
    assert result.invite.id is not None
    assert result.invite.token_hash == hash_token(result.token)
    assert result.invite.role == UserRole.member.value
    assert result.invite.ttl_seconds == 86400
    assert result.invite.generated_by_user_id == _ADMIN
    assert result.invite.generated_at.tzinfo is not None
    assert result.invite.used_at is None
    assert result.invite.used_by_user_id is None
    assert result.invite.used_from_ip is None
    assert result.invite.revoked_at is None

    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        assert row is not None
        assert row.token_hash == hash_token(result.token)

    raw = await fake_redis.get(f"invite:token:{result.token}")
    assert raw is not None
    payload = json.loads(raw)
    assert payload["invite_id"] == str(result.invite.id)
    assert payload["role"] == "member"
    assert payload["generated_by_user_id"] == str(_ADMIN)
    assert "generated_at" in payload

    ttl = await fake_redis.ttl(f"invite:token:{result.token}")
    assert abs(ttl - 86400) <= 1


async def test_generate_invite_returns_cleartext_token_only_in_result(service):
    r1 = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )
    r2 = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )

    assert r1.token != r2.token
    assert r1.invite.token_hash != r2.invite.token_hash

    with Session(get_engine()) as s:
        for invite_id in (r1.invite.id, r2.invite.id):
            row = s.get(InviteToken, invite_id)
            assert row is not None
            # Cleartext never persisted -- the row only has the hash column.
            assert not hasattr(row, "token") or getattr(row, "token", None) in (None, "")


async def test_generate_invite_rejects_short_ttl(service, fake_redis):
    with pytest.raises(ValueError, match=">= 60"):
        await service.generate_invite(
            role=UserRole.member, ttl_seconds=59, generated_by_user_id=_ADMIN
        )
    with Session(get_engine()) as s:
        assert s.exec(select(InviteToken)).all() == []
    keys = [k async for k in fake_redis.scan_iter(match="invite:token:*")]
    assert keys == []


async def test_generate_invite_rejects_long_ttl(service, fake_redis):
    with pytest.raises(ValueError, match="<= 7776000"):
        await service.generate_invite(
            role=UserRole.member, ttl_seconds=7776001, generated_by_user_id=_ADMIN
        )
    with Session(get_engine()) as s:
        assert s.exec(select(InviteToken)).all() == []
    keys = [k async for k in fake_redis.scan_iter(match="invite:token:*")]
    assert keys == []


async def test_generate_invite_rejects_agent_role(service, fake_redis):
    with pytest.raises(ValueError, match="member or admin"):
        await service.generate_invite(
            role=UserRole.agent, ttl_seconds=86400, generated_by_user_id=_ADMIN
        )
    with Session(get_engine()) as s:
        assert s.exec(select(InviteToken)).all() == []
    keys = [k async for k in fake_redis.scan_iter(match="invite:token:*")]
    assert keys == []


async def test_generate_invite_rolls_back_on_redis_failure(fake_redis):
    """Redis SET failure leaves DB row as audit history; exception propagates."""
    fake_redis.set = AsyncMock(side_effect=ConnectionError("boom"))
    svc = InviteService(redis=fake_redis, engine=get_engine())

    with pytest.raises(ConnectionError, match="boom"):
        await svc.generate_invite(
            role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
        )

    with Session(get_engine()) as s:
        rows = s.exec(select(InviteToken)).all()
        assert len(rows) == 1
        assert rows[0].generated_by_user_id == _ADMIN
        assert rows[0].used_at is None
        assert rows[0].revoked_at is None


# ---------------------------------------------------------------------------
# validate_active() — AC-2
# ---------------------------------------------------------------------------


async def test_validate_active_returns_view_object_for_active_invite(service):
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )

    view = await service.validate_active(result.token)
    assert isinstance(view, ActiveInvite)
    assert view.invite_id == result.invite.id
    assert view.role == UserRole.member
    assert view.generated_by_user_id == _ADMIN
    assert view.generated_at.tzinfo is not None


async def test_validate_active_returns_none_for_unknown_token(service):
    assert (await service.validate_active("nonexistent-token-xyz")) is None


async def test_validate_active_returns_none_after_redis_expiry(service, fake_redis):
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )
    # Simulate Redis TTL expiry by directly DEL-ing the key (fakeredis honours
    # EXPIRE only with explicit time_machine advance).
    await fake_redis.delete(f"invite:token:{result.token}")
    assert (await service.validate_active(result.token)) is None

    # But the DB row is still present (audit history outlives Redis TTL).
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        assert row is not None
        assert row.used_at is None
        assert row.revoked_at is None


async def test_validate_active_does_not_touch_db(fake_redis):
    """A fake engine that raises on connect() proves Redis-only path."""
    result = await InviteService(redis=fake_redis, engine=get_engine()).generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )

    booby = MagicMock(spec=Engine)
    booby.connect.side_effect = AssertionError("DB touched")
    svc = InviteService(redis=fake_redis, engine=booby)

    view = await svc.validate_active(result.token)
    assert view is not None
    assert view.invite_id == result.invite.id

    assert (await svc.validate_active("nope")) is None
    booby.connect.assert_not_called()


# ---------------------------------------------------------------------------
# consume() — AC-3
# ---------------------------------------------------------------------------


async def test_consume_marks_db_row_and_deletes_redis_key(service, fake_redis):
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )

    consumed = await service.consume(
        result.token, used_by_user_id=_USER, used_from_ip="203.0.113.42"
    )
    assert consumed.used_by_user_id == _USER
    assert consumed.used_from_ip == "203.0.113.42"
    assert consumed.used_at is not None
    assert consumed.used_at.tzinfo is not None
    delta = abs((datetime.datetime.now(datetime.UTC) - consumed.used_at).total_seconds())
    assert delta < 5

    # DB persists the state
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        assert row.used_by_user_id == _USER
        assert row.used_from_ip == "203.0.113.42"
        assert row.used_at is not None

    # Redis key gone
    assert (await fake_redis.get(f"invite:token:{result.token}")) is None


async def test_consume_second_call_raises_invite_consumed(service):
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )
    await service.consume(result.token, used_by_user_id=_USER, used_from_ip="1.2.3.4")

    with pytest.raises(InviteConsumed):
        await service.consume(result.token, used_by_user_id=_OTHER, used_from_ip="198.51.100.7")

    # Original state preserved
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        assert row.used_by_user_id == _USER
        assert row.used_from_ip == "1.2.3.4"


async def test_consume_unknown_token_raises_invite_consumed(service):
    with pytest.raises(InviteConsumed):
        await service.consume("never-existed-token", used_by_user_id=_USER, used_from_ip="1.2.3.4")


async def test_consume_db_row_predicate_blocks_replay_on_stale_redis(service, fake_redis):
    """DB row with used_at already set must defeat stale Redis cache."""
    now = datetime.datetime.now(datetime.UTC)
    cleartext = "fake-token-zzzzzzzzzzzzzz"
    invite_id = uuid.uuid4()

    # Pre-seed DB: row already consumed
    with Session(get_engine()) as s:
        row = InviteToken(
            id=invite_id,
            token_hash=hash_token(cleartext),
            role="member",
            ttl_seconds=86400,
            generated_by_user_id=_ADMIN,
            generated_at=now,
            used_at=now,
            used_by_user_id=_USER,
            used_from_ip="1.1.1.1",
        )
        s.add(row)
        s.commit()

    # Pre-seed Redis: as if still active
    payload = json.dumps(
        {
            "invite_id": str(invite_id),
            "token_hash": hash_token(cleartext),
            "role": "member",
            "generated_by_user_id": str(_ADMIN),
            "generated_at": now.isoformat(),
        }
    )
    await fake_redis.set(f"invite:token:{cleartext}", payload, ex=86400)

    with pytest.raises(InviteConsumed):
        await service.consume(cleartext, used_by_user_id=_OTHER, used_from_ip="2.2.2.2")

    with Session(get_engine()) as s:
        again = s.get(InviteToken, invite_id)
        assert again.used_by_user_id == _USER  # unchanged
        assert again.used_from_ip == "1.1.1.1"


async def test_consume_revoked_invite_raises_invite_consumed(service, fake_redis):
    """A revoked-but-still-in-Redis invite must surface as InviteConsumed."""
    now = datetime.datetime.now(datetime.UTC)
    cleartext = "revoked-token-aaaaaaaaaaa"
    invite_id = uuid.uuid4()

    with Session(get_engine()) as s:
        row = InviteToken(
            id=invite_id,
            token_hash=hash_token(cleartext),
            role="member",
            ttl_seconds=86400,
            generated_by_user_id=_ADMIN,
            generated_at=now,
            revoked_at=now,
        )
        s.add(row)
        s.commit()

    payload = json.dumps(
        {
            "invite_id": str(invite_id),
            "token_hash": hash_token(cleartext),
            "role": "member",
            "generated_by_user_id": str(_ADMIN),
            "generated_at": now.isoformat(),
        }
    )
    await fake_redis.set(f"invite:token:{cleartext}", payload, ex=86400)

    with pytest.raises(InviteConsumed):
        await service.consume(cleartext, used_by_user_id=_USER, used_from_ip="3.3.3.3")


# ---------------------------------------------------------------------------
# revoke() — AC-4
# ---------------------------------------------------------------------------


async def test_revoke_marks_db_row_and_deletes_redis_key(service, fake_redis):
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )

    revoked = await service.revoke(result.invite.id)
    assert revoked.revoked_at is not None
    assert revoked.revoked_at.tzinfo is not None
    delta = abs((datetime.datetime.now(datetime.UTC) - revoked.revoked_at).total_seconds())
    assert delta < 5

    # DB persists revoke
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        assert row.revoked_at is not None

    # Redis key removed
    assert (await fake_redis.get(f"invite:token:{result.token}")) is None


async def test_revoke_already_revoked_raises_invite_already_resolved(service):
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )
    first = await service.revoke(result.invite.id)
    first_revoked_at = first.revoked_at

    with pytest.raises(InviteAlreadyResolved):
        await service.revoke(result.invite.id)

    # First revoke's timestamp preserved
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        assert row.revoked_at == first_revoked_at


async def test_revoke_already_consumed_raises_invite_already_resolved(service):
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )
    await service.consume(result.token, used_by_user_id=_USER, used_from_ip="1.2.3.4")

    with pytest.raises(InviteAlreadyResolved):
        await service.revoke(result.invite.id)


async def test_revoke_unknown_id_raises_invite_not_found(service):
    with pytest.raises(InviteNotFound):
        await service.revoke(uuid.uuid4())


# ---------------------------------------------------------------------------
# revoke()/consume() race regression — Story 6.2 P2 fix (AC-4 atomicity)
# ---------------------------------------------------------------------------


async def test_revoke_loses_race_to_consume_raises_already_resolved(service):
    """If consume commits between admin revoke's read and write, the
    conditional UPDATE must reject the revoke instead of clobbering used_at."""
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )

    # Simulate the racing consume committing first: directly set used_at on
    # the DB row, leaving revoked_at NULL. A naive read-then-write revoke
    # would happily proceed and populate revoked_at on top of used_at.
    now = datetime.datetime.now(datetime.UTC)
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        row.used_at = now
        row.used_by_user_id = _USER
        row.used_from_ip = "9.9.9.9"
        s.add(row)
        s.commit()

    with pytest.raises(InviteAlreadyResolved):
        await service.revoke(result.invite.id)

    # Used state preserved, revoked_at never set -- single resolution invariant.
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        assert row.used_at is not None
        assert row.used_by_user_id == _USER
        assert row.revoked_at is None


async def test_consume_loses_race_to_revoke_raises_appropriate_error(service, fake_redis):
    """If revoke commits between consume's Redis read and DB write, the
    conditional UPDATE on used_at/revoked_at IS NULL must reject the consume.

    Public-facing error stays InviteConsumed (token-status enumeration guard --
    consumed/revoked/expired all surface uniformly per FR5-INVITE-4)."""
    result = await service.generate_invite(
        role=UserRole.member, ttl_seconds=86400, generated_by_user_id=_ADMIN
    )

    # Simulate the racing revoke committing first: set revoked_at directly on
    # the DB row but leave the Redis key in place (the real race window --
    # revoke's `await self._redis.delete(...)` hasn't run yet when consume
    # does its Redis GET).
    now = datetime.datetime.now(datetime.UTC)
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        row.revoked_at = now
        s.add(row)
        s.commit()

    assert (await fake_redis.get(f"invite:token:{result.token}")) is not None

    with pytest.raises(InviteConsumed):
        await service.consume(result.token, used_by_user_id=_OTHER, used_from_ip="4.4.4.4")

    # Revoked state preserved, used_at never set -- single resolution invariant.
    with Session(get_engine()) as s:
        row = s.get(InviteToken, result.invite.id)
        assert row.revoked_at is not None
        assert row.used_at is None
        assert row.used_by_user_id is None
