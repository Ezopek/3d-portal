import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth.dependencies import current_admin
from app.core.auth.jwt import encode_token
from app.core.config import get_settings

# A fixed UUID used as the subject in dependency tests.
_ADMIN_UUID = "00000000-0000-0000-0000-000000000007"


@pytest.fixture
def app_with_protected_route():
    app = FastAPI()

    @app.get("/protected")
    def _route(user_id: uuid.UUID = current_admin):
        return {"user_id": str(user_id)}

    return app


def test_no_token_returns_401(app_with_protected_route):
    client = TestClient(app_with_protected_route)
    assert client.get("/protected").status_code == 401


def test_valid_admin_token_returns_subject(app_with_protected_route):
    settings = get_settings()
    token = encode_token(
        subject=_ADMIN_UUID,
        role="admin",
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    client = TestClient(app_with_protected_route)
    r = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"user_id": _ADMIN_UUID}


def test_member_role_returns_403(app_with_protected_route):
    settings = get_settings()
    token = encode_token(
        subject=_ADMIN_UUID,
        role="member",
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    client = TestClient(app_with_protected_route)
    r = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
