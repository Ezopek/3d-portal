from datetime import datetime

from app.core.db.models import AuditEvent, User, UserRole


def test_user_role_enum_values():
    assert UserRole.admin.value == "admin"
    assert UserRole.member.value == "member"


def test_user_table_metadata():
    assert User.__tablename__ == "user"
    assert "email" in User.model_fields
    assert "password_hash" in User.model_fields
    assert "role" in User.model_fields


def test_audit_event_defaults_now():
    event = AuditEvent(kind="test", payload="{}")
    assert isinstance(event.at, datetime)


from sqlmodel import Session, select

from app.core.db.session import create_engine_for_url, init_schema


def test_engine_can_create_schema(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    init_schema(engine)
    with Session(engine) as session:
        result = session.exec(select(User)).all()
        assert result == []
