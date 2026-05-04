"""Tests for the agent service-account bootstrap script."""

from sqlmodel import Session, select

from app.core.auth.password import verify_password
from app.core.db.models import User, UserRole
from app.core.db.session import get_engine
from scripts.bootstrap_agent import bootstrap_agent


def test_bootstrap_creates_new_agent_user():
    user, action, password = bootstrap_agent(email="agent-t1@portal.example.com")
    assert action == "created"
    assert user.role == UserRole.agent
    assert user.email == "agent-t1@portal.example.com"
    assert len(password) == 32

    # Round-trip: hashed password should verify against cleartext
    with Session(get_engine()) as s:
        row = s.exec(select(User).where(User.email == "agent-t1@portal.example.com")).first()
    assert verify_password(password, row.password_hash)


def test_bootstrap_idempotent_on_existing_email():
    bootstrap_agent(email="agent-t2@portal.example.com")
    user, action, password = bootstrap_agent(email="agent-t2@portal.example.com")
    assert action == "exists"
    assert password == ""  # no new password issued
    assert user.email == "agent-t2@portal.example.com"


def test_bootstrap_rotate_replaces_password():
    _, _, original = bootstrap_agent(email="agent-t3@portal.example.com")
    _user, action, new_password = bootstrap_agent(email="agent-t3@portal.example.com", rotate=True)
    assert action == "rotated"
    assert new_password != original

    with Session(get_engine()) as s:
        row = s.exec(select(User).where(User.email == "agent-t3@portal.example.com")).first()
    assert verify_password(new_password, row.password_hash)
    assert not verify_password(original, row.password_hash)


def test_bootstrap_accepts_custom_password():
    custom = "deliberately-weak-for-test-only-not-random"
    _user, action, password = bootstrap_agent(email="agent-t4@portal.example.com", password=custom)
    assert action == "created"
    assert password == custom
    with Session(get_engine()) as s:
        row = s.exec(select(User).where(User.email == "agent-t4@portal.example.com")).first()
    assert verify_password(custom, row.password_hash)


def test_bootstrap_login_e2e_works(client):
    """Bootstrap an agent, then log in via the public API and verify the JWT
    decodes to the agent's id with role=agent."""
    import jwt as _jwt

    from app.core.config import get_settings

    user, _, password = bootstrap_agent(email="agent-e2e@portal.example.com")

    r = client.post(
        "/api/auth/login",
        json={"email": "agent-e2e@portal.example.com", "password": password},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    claims = _jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    assert claims["role"] == "agent"
    assert claims["sub"] == str(user.id)


def test_bootstrap_agent_can_call_admin_endpoints(client):
    """Sanity: an agent JWT is accepted by current_admin_or_agent dep,
    so the agent can hit /api/admin/* endpoints (with the role-gated
    exceptions like ?hard=true). Smoke against POST /api/admin/categories."""
    _user, _, password = bootstrap_agent(email="agent-call@portal.example.com")

    r = client.post(
        "/api/auth/login",
        json={"email": "agent-call@portal.example.com", "password": password},
    )
    token = r.json()["access_token"]

    # Use a unique slug so this test stays independent
    r2 = client.post(
        "/api/admin/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"slug": "agent-bootstrap-smoke", "name_en": "Smoke"},
    )
    assert r2.status_code == 201, r2.text
