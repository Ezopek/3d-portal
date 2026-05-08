"""RefreshToken model — round-trip and constraints."""
import datetime
import string
import uuid

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.db.models import RefreshToken, User
from app.core.auth.refresh import (
    generate_refresh_secret,
    hash_refresh_secret,
    new_refresh_row,
    rotate_refresh,
    RotationOutcome,
    GRACE_SECONDS,
    REFRESH_TTL_DAYS,
)


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


def test_generate_secret_is_url_safe_and_unique():
    a = generate_refresh_secret()
    b = generate_refresh_secret()
    assert len(a) >= 32
    assert a != b
    # url-safe alphabet only
    allowed = set(string.ascii_letters + string.digits + "-_")
    assert set(a).issubset(allowed)


def test_hash_is_deterministic_hex_64():
    h = hash_refresh_secret("abc")
    assert len(h) == 64
    assert hash_refresh_secret("abc") == h
    assert hash_refresh_secret("abd") != h


def test_new_refresh_row_sets_invariants(engine):
    """new_refresh_row populates issued_at/expires_at/family_issued_at correctly."""
    with Session(engine) as s:
        u = User(
            id=uuid.uuid4(), email="u@x", display_name="U", role="admin",
            password_hash="x", created_at=datetime.datetime.now(datetime.UTC),
        )
        s.add(u); s.commit(); s.refresh(u)
        secret, row = new_refresh_row(
            user_id=u.id, family_id=None,  # None → start a new family
            family_issued_at=None, ip="127.0.0.1", user_agent="UA",
        )
        s.add(row); s.commit(); s.refresh(row)
        assert row.family_id is not None
        assert row.family_issued_at == row.issued_at
        delta = row.expires_at - row.issued_at
        assert delta == datetime.timedelta(days=REFRESH_TTL_DAYS)
        assert hash_refresh_secret(secret) == row.token_hash
