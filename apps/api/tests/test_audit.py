import json

from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.db.models import AuditEvent, User, UserRole
from app.core.db.session import create_engine_for_url, init_schema


def test_record_event_persists_with_payload(tmp_path):
    engine = create_engine_for_url(f"sqlite:///{tmp_path}/a.db")
    init_schema(engine)
    # Seed a user so the actor_user_id FK constraint is satisfied
    with Session(engine) as s:
        u = User(
            email="a@b.c",
            display_name="Test",
            role=UserRole.admin,
            password_hash="pw",
        )
        s.add(u)
        s.commit()
        s.refresh(u)
        user_id = u.id

    record_event(
        engine, kind="auth.login.success", actor_user_id=user_id, payload={"email": "a@b.c"}
    )
    with Session(engine) as s:
        events = s.exec(select(AuditEvent)).all()
    assert len(events) == 1
    assert events[0].kind == "auth.login.success"
    assert events[0].actor_user_id == user_id
    assert json.loads(events[0].payload) == {"email": "a@b.c"}
