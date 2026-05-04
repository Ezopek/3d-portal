import pytest
from sqlmodel import Session, select

from app.core.audit import KNOWN_ENTITY_TYPES, record_event
from app.core.db.models import AuditLog, User, UserRole
from app.core.db.session import create_engine_for_url, init_schema


def test_record_event_persists(tmp_path):
    db_path = tmp_path / "audit_test.db"
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    init_schema(engine)

    with Session(engine) as session:
        u = User(
            email="a@b.c",
            display_name="A",
            role=UserRole.admin,
            password_hash="x",
        )
        session.add(u)
        session.commit()
        session.refresh(u)
        user_id = u.id

    record_event(
        engine,
        action="auth.login.success",
        entity_type="user",
        entity_id=user_id,
        actor_user_id=user_id,
        after={"email": "a@b.c"},
    )

    with Session(engine) as session:
        events = session.exec(select(AuditLog)).all()

    assert len(events) == 1
    assert events[0].actor_user_id == user_id
    assert events[0].action == "auth.login.success"
    assert events[0].entity_type == "user"
    assert events[0].entity_id == user_id
    assert events[0].after_json is not None
    assert '"email": "a@b.c"' in events[0].after_json


def test_record_event_rejects_unknown_entity_type(tmp_path):
    """Forward guard for Slice 2's enum tightening — drift dies fast."""
    db_path = tmp_path / "audit_unknown.db"
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    init_schema(engine)

    with pytest.raises(ValueError, match="unknown entity_type"):
        record_event(
            engine,
            action="x",
            entity_type="not_a_real_resource",
            entity_id=None,
            actor_user_id=None,
        )


def test_known_entity_types_covers_all_call_site_resources():
    """All resources currently audit-logged in app/modules/ must be in the set."""
    expected = {
        "catalog",
        "model",
        "render_selection",
        "share_token",
        "thumbnail_override",
        "user",
    }
    assert expected == KNOWN_ENTITY_TYPES
