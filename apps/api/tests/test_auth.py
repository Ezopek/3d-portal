def test_login_with_valid_credentials_returns_jwt(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "test-admin-pw"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60


def test_login_with_wrong_password_returns_401(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "nope"},
    )
    assert r.status_code == 401


def test_me_with_token_returns_user(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "test-admin-pw"},
    )
    token = r.json()["access_token"]
    r2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["email"] == "admin@localhost.localdomain"
    assert body["role"] == "admin"


def test_me_without_token_returns_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_logout_returns_204(client):
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
