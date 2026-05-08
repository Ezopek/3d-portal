def test_login_with_valid_credentials_returns_user(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "test-admin-pw"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "user" in body
    assert body["user"]["email"] == "admin@localhost.localdomain"
    assert body["user"]["role"] == "admin"
    assert "access_token" not in body


def test_login_with_wrong_password_returns_401(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "nope"},
    )
    assert r.status_code == 401


def test_me_with_token_returns_user(client):
    import uuid

    client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "test-admin-pw"},
    )
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200
    body = r2.json()
    assert body["email"] == "admin@localhost.localdomain"
    assert body["role"] == "admin"
    # Lock the public contract: `id` must round-trip as a UUID string.
    assert "id" in body
    uuid.UUID(body["id"])  # raises if malformed


def test_me_without_token_returns_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_logout_returns_204(client):
    r = client.post("/api/auth/logout")
    assert r.status_code == 204


def test_me_with_member_token_returns_user(client):
    """Member role can fetch their own /me — needed for AuthContext on FE."""
    from sqlmodel import Session

    from app.core.auth.password import hash_password
    from app.core.db.models import User, UserRole
    from app.core.db.session import get_engine

    with Session(get_engine()) as s:
        member = User(
            email="member-me@portal.example.com",
            display_name="Test Member",
            role=UserRole.member,
            password_hash=hash_password("member-pw"),
        )
        s.add(member)
        s.commit()

    r = client.post(
        "/api/auth/login",
        json={"email": "member-me@portal.example.com", "password": "member-pw"},
    )
    assert r.status_code == 200
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200
    body = r2.json()
    assert body["email"] == "member-me@portal.example.com"
    assert body["role"] == "member"
    assert body["display_name"] == "Test Member"


def test_me_with_agent_token_returns_user(client):
    """Agent role can fetch its own /me — symmetry with member; backend should
    not gate /me by role (only by authenticated-or-not)."""
    from scripts.bootstrap_agent import bootstrap_agent

    _user, _, password = bootstrap_agent(email="agent-me@portal.example.com")

    r = client.post(
        "/api/auth/login",
        json={"email": "agent-me@portal.example.com", "password": password},
    )
    assert r.status_code == 200
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200
    assert r2.json()["role"] == "agent"
