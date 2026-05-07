"""RefreshToken model — round-trip and constraints."""
import datetime
import uuid

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.db.models import RefreshToken, User


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(e)
    yield e
    e.dispose()


def test_refresh_token_round_trip(engine):
    with Session(engine) as s:
        u = User(
            id=uuid.uuid4(),
            email="u@x",
            display_name="U",
            role="admin",
            password_hash="x",
            created_at=datetime.datetime.now(datetime.UTC),
        )
        s.add(u)
        s.commit()
        s.refresh(u)
        rt = RefreshToken(
            id=uuid.uuid4(),
            user_id=u.id,
            family_id=uuid.uuid4(),
            family_issued_at=datetime.datetime.now(datetime.UTC),
            token_hash="abc123",
            issued_at=datetime.datetime.now(datetime.UTC),
            expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30),
        )
        s.add(rt)
        s.commit()
        s.refresh(rt)
        assert rt.id is not None
        assert rt.user_id == u.id
        assert rt.revoked_at is None
        assert rt.replaced_by_id is None
