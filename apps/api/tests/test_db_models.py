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
