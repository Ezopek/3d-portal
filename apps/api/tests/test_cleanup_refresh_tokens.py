"""apps/api/tests/test_cleanup_refresh_tokens.py"""
import datetime
import uuid

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.db.models import RefreshToken, User
from app.workers.cleanup_refresh_tokens import cleanup_refresh_tokens_sync


@pytest.fixture
def engine_with_user():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(e)
    with Session(e) as s:
        u = User(
            id=uuid.uuid4(), email="a@example.com", display_name="a", role="admin",
            password_hash="x",
            created_at=datetime.datetime.now(datetime.UTC),
        )
        s.add(u)
        s.commit()
        yield e, u.id
    e.dispose()


def _row(user_id, **overrides):
    base = dict(
        id=uuid.uuid4(),
        user_id=user_id,
        family_id=uuid.uuid4(),
        family_issued_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        token_hash=uuid.uuid4().hex,
        issued_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        expires_at=datetime.datetime(2026, 12, 31, tzinfo=datetime.UTC),
    )
    base.update(overrides)
    return RefreshToken(**base)


def test_cleanup_deletes_old_revoked_and_expired(engine_with_user):
    engine, user_id = engine_with_user
    long_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=10)
    just_now = datetime.datetime.now(datetime.UTC)
    with Session(engine) as s:
        s.add(_row(user_id, revoked_at=long_ago, revoke_reason="logout"))   # delete (old revoke)
        s.add(_row(user_id, revoked_at=just_now, revoke_reason="logout"))   # keep (recent revoke)
        s.add(_row(user_id, expires_at=long_ago))                            # delete (old expiry)
        s.add(_row(user_id))                                                 # keep (active)
        s.commit()

    deleted = cleanup_refresh_tokens_sync(engine)
    assert deleted == 2

    with Session(engine) as s:
        remaining = s.exec(select(RefreshToken)).all()
        assert len(remaining) == 2
