"""apps/api/tests/test_auth_refresh.py"""
import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.cookies import ACCESS_COOKIE, REFRESH_COOKIE
from app.core.db.models import RefreshToken
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "p")
    monkeypatch.setenv("JWT_SECRET", "s")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    get_settings.cache_clear()
    get_engine.cache_clear()
    with TestClient(create_app()) as c:
        c.headers.update({"X-Portal-Client": "web"})
        c.post("/api/auth/login",
               json={"email": "admin@example.com", "password": "p"})
        yield c
    get_settings.cache_clear()
    get_engine.cache_clear()


def _get_refresh_cookie(client) -> str | None:
    """Read the refresh cookie, tolerating multiple path entries."""
    values = [ck.value for ck in client.cookies.jar if ck.name == REFRESH_COOKIE]
    return values[-1] if values else None


def test_refresh_happy_path_rotates(client):
    old_refresh = _get_refresh_cookie(client)
    old_access = client.cookies.get(ACCESS_COOKIE)
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200
    new_refresh = _get_refresh_cookie(client)
    new_access = client.cookies.get(ACCESS_COOKIE)
    assert new_refresh != old_refresh
    assert new_access != old_access
    body = r.json()
    assert body["user"]["email"] == "admin@example.com"


def test_refresh_with_no_cookie_returns_no_refresh(client):
    client.cookies.delete(REFRESH_COOKIE)
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401
    assert r.json()["detail"] == "no_refresh"


def test_refresh_with_garbage_returns_invalid_refresh(client):
    client.cookies.set(REFRESH_COOKIE, "garbage", path="/api/auth")
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_refresh"


def test_refresh_with_expired_returns_refresh_expired(client):
    """Backdate expires_at on the active row."""
    from app.core.db.session import get_engine
    with Session(get_engine()) as s:
        row = s.exec(select(RefreshToken)).first()
        row.expires_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=1)
        s.add(row)
        s.commit()
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401
    assert r.json()["detail"] == "refresh_expired"


def test_grace_returns_active_descendant_on_ua_match(client):
    """Scenario: rotate once, then present the OLD refresh again with same UA → grace path.

    The server cannot return the raw secret of the active descendant (only its hash is stored),
    so it issues a fresh rotation from the active row. The invariants are:
      1. Status 200 — not denied.
      2. The response sets a new refresh cookie different from old_refresh.
      3. The family is NOT burned — exactly one active row remains.
    """
    old_refresh = _get_refresh_cookie(client)
    # First rotation
    client.post("/api/auth/refresh", headers={"User-Agent": "UA-1"})
    new_refresh = _get_refresh_cookie(client)
    assert new_refresh != old_refresh
    # Now present old (within grace, same UA) — replace current cookie in jar.
    for ck in list(client.cookies.jar):
        if ck.name == REFRESH_COOKIE:
            client.cookies.jar.clear(ck.domain, ck.path, ck.name)
    client.cookies.set(REFRESH_COOKIE, old_refresh)
    r = client.post("/api/auth/refresh", headers={"User-Agent": "UA-1"})
    assert r.status_code == 200
    # The response sets a fresh token (rotated from active row) — different from old_refresh.
    served_in_response = r.cookies.get(REFRESH_COOKIE)
    assert served_in_response is not None
    assert served_in_response != old_refresh

    # And the family is NOT burned — exactly one active row.
    from app.core.db.session import get_engine
    with Session(get_engine()) as s:
        active = s.exec(
            select(RefreshToken).where(RefreshToken.revoked_at.is_(None))
        ).all()
        assert len(active) == 1


def test_grace_ua_mismatch_denies_without_burning_family(client):
    old_refresh = _get_refresh_cookie(client)
    client.post("/api/auth/refresh", headers={"User-Agent": "UA-1"})
    # Now present old with a different UA — replace current cookie in jar.
    for ck in list(client.cookies.jar):
        if ck.name == REFRESH_COOKIE:
            client.cookies.jar.clear(ck.domain, ck.path, ck.name)
    client.cookies.set(REFRESH_COOKIE, old_refresh)
    r = client.post("/api/auth/refresh", headers={"User-Agent": "UA-2"})
    assert r.status_code == 401
    assert r.json()["detail"] == "force_relogin"
    # Family NOT burned — active row still alive.
    from app.core.db.session import get_engine
    with Session(get_engine()) as s:
        active = s.exec(
            select(RefreshToken).where(RefreshToken.revoked_at.is_(None))
        ).all()
        assert len(active) == 1


def test_reuse_outside_grace_burns_family(client):
    """Rotate, sleep past grace, present old → reuse_detected + family burned."""
    old_refresh = _get_refresh_cookie(client)
    client.post("/api/auth/refresh", headers={"User-Agent": "UA"})

    # Backdate the rotated row's replaced_at past the grace window.
    from app.core.db.session import get_engine
    with Session(get_engine()) as s:
        rotated = s.exec(
            select(RefreshToken).where(RefreshToken.revoke_reason == "rotated")
        ).first()
        rotated.replaced_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=60)
        s.add(rotated)
        s.commit()

    for ck in list(client.cookies.jar):
        if ck.name == REFRESH_COOKIE:
            client.cookies.jar.clear(ck.domain, ck.path, ck.name)
    client.cookies.set(REFRESH_COOKIE, old_refresh)
    r = client.post("/api/auth/refresh", headers={"User-Agent": "UA"})
    assert r.status_code == 401
    assert r.json()["detail"] == "force_relogin"

    # All rows in the family are revoked.
    with Session(get_engine()) as s:
        active = s.exec(
            select(RefreshToken).where(RefreshToken.revoked_at.is_(None))
        ).all()
        assert active == []


def test_concurrent_refresh_one_wins(client):
    """Two parallel rotations on the same refresh — both succeed (one rotates, one grace)."""
    import threading
    results: list[int] = []
    cookies_snapshot = dict(client.cookies)

    def _hit():
        with TestClient(client.app) as c:
            c.headers.update({"X-Portal-Client": "web"})
            for k, v in cookies_snapshot.items():
                c.cookies.set(k, v)
            r = c.post("/api/auth/refresh", headers={"User-Agent": "UA"})
            results.append(r.status_code)

    t1 = threading.Thread(target=_hit)
    t2 = threading.Thread(target=_hit)
    t1.start(); t2.start()
    t1.join(); t2.join()
    # At least one must succeed (200). The other can be 200 (grace) or 401 race-lost.
    # The CRITICAL invariant is that the family ends with exactly one active token.
    assert 200 in results

    from app.core.db.session import get_engine
    with Session(get_engine()) as s:
        active = s.exec(
            select(RefreshToken).where(RefreshToken.revoked_at.is_(None))
        ).all()
        assert len(active) == 1, f"expected 1 active row, got {len(active)}"
