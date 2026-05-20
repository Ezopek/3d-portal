"""Tests for Initiative 6 Story 11.2 — share-scoped asset endpoint (Decision N).

Endpoint under test: GET /api/share/{token}/files/{file_id}/content

Hardened-(a) per Codex peer-grill 2026-05-20 (SCP §3.4.2):
- Kind filter: only ModelFileKind.image / .print / .stl are surfaced via share
  (source + archive_3mf are NEVER exposed)
- Soft-delete filter: model.deleted_at IS NOT NULL → uniform 404
- Uniform 404 error shape: no enumeration oracle between wrong-token /
  wrong-model / wrong-kind / soft-deleted / missing-row
- Cache-Control: no-store: revoked tokens cannot serve cached content
- No ETag: premature ETag-match would short-circuit the scope check
- Audit emission: target_token_hash (sha256 hex), NEVER clear token
- Path-token redaction: logging.py regex masks /api/share/<bearer>/...

12 IDOR matrix tests + 3 cross-validation tests + extras (12+3+ test count
per epics.md Story 11.2 acceptance).
"""

import hashlib
import logging
import uuid
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.config import get_settings
from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    ModelFile,
    ModelFileKind,
    User,
)
from app.core.db.session import get_engine
from app.main import create_app


@pytest.fixture
def share_fixture(tmp_path, monkeypatch):
    """Build a fresh app + DB + fakeredis + on-disk content with seeded data.

    Yields a `(client, token_valid, ids)` tuple where:
        - client: TestClient bound to a per-test app
        - token_valid: live share-token resolving to model_a
        - ids: dict containing model_a + model_b + file uuids by kind +
               revoked_token + soft_deleted_token for negative-path tests
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/share-asset.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-real")
    monkeypatch.setenv("PORTAL_CONTENT_DIR", str(tmp_path / "portal-content"))
    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose

    storage_root = (tmp_path / "portal-content").resolve()
    storage_root.mkdir(parents=True, exist_ok=True)

    def _seed_file(session, model, *, kind, original_name, content):
        file_uuid = uuid.uuid4()
        rel = f"models/{model.id}/files/{file_uuid}.bin"
        (storage_root / rel).parent.mkdir(parents=True, exist_ok=True)
        (storage_root / rel).write_bytes(content)
        mf = ModelFile(
            id=file_uuid,
            model_id=model.id,
            kind=kind,
            original_name=original_name,
            storage_path=rel,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            mime_type="image/png" if kind == ModelFileKind.image else "application/octet-stream",
        )
        session.add(mf)
        session.commit()
        session.refresh(mf)
        return mf

    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        app.state.redis = factory

        import datetime

        engine = get_engine()
        with Session(engine) as s:
            admin = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            admin_id = admin.id

            cat = Category(slug=f"sa-cat-{uuid.uuid4().hex[:6]}", name_en="ShareAsset")
            s.add(cat)
            s.commit()
            s.refresh(cat)
            cat_id = cat.id

            model_a = Model(
                slug=f"sa-model-a-{uuid.uuid4().hex[:6]}",
                name_en="Model A",
                category_id=cat_id,
            )
            s.add(model_a)
            s.commit()
            s.refresh(model_a)
            model_a_id = model_a.id

            model_b = Model(
                slug=f"sa-model-b-{uuid.uuid4().hex[:6]}",
                name_en="Model B",
                category_id=cat_id,
            )
            s.add(model_b)
            s.commit()
            s.refresh(model_b)
            model_b_id = model_b.id

            img_a = _seed_file(
                s, model_a, kind=ModelFileKind.image, original_name="img.png", content=b"IMG_A"
            )
            stl_a = _seed_file(
                s, model_a, kind=ModelFileKind.stl, original_name="m.stl", content=b"STL_A"
            )
            src_a = _seed_file(
                s,
                model_a,
                kind=ModelFileKind.source,
                original_name="raw.blend",
                content=b"SRC_A",
            )
            img_b = _seed_file(
                s, model_b, kind=ModelFileKind.image, original_name="img.png", content=b"IMG_B"
            )
            img_a_id = img_a.id
            stl_a_id = stl_a.id
            src_a_id = src_a.id
            img_b_id = img_b.id

            model_soft = Model(
                slug=f"sa-model-soft-{uuid.uuid4().hex[:6]}",
                name_en="Soft Deleted",
                category_id=cat_id,
            )
            s.add(model_soft)
            s.commit()
            s.refresh(model_soft)
            soft_img = _seed_file(
                s,
                model_soft,
                kind=ModelFileKind.image,
                original_name="soft.png",
                content=b"SOFT",
            )
            model_soft_id = model_soft.id
            soft_img_id = soft_img.id

        admin_jwt = encode_token(
            subject=str(admin_id), role="admin", secret="test-secret-not-real", ttl_minutes=30
        )
        member_jwt = encode_token(
            subject=str(uuid.uuid4()), role="member", secret="test-secret-not-real", ttl_minutes=30
        )

        # Mint share token for model_a via the admin endpoint (canonical path)
        c.cookies.set(ACCESS_COOKIE, admin_jwt)
        created_resp = c.post(
            "/api/admin/share",
            json={"model_id": str(model_a_id), "expires_in_hours": 1},
        )
        assert created_resp.status_code in (200, 201), created_resp.text
        token_valid = created_resp.json()["token"]

        # Mint a second share token for revoke testing
        created_revoked = c.post(
            "/api/admin/share",
            json={"model_id": str(model_a_id), "expires_in_hours": 1},
        )
        assert created_revoked.status_code in (200, 201)
        token_to_revoke = created_revoked.json()["token"]
        # Revoke immediately
        revoke_resp = c.delete(f"/api/admin/share/{token_to_revoke}")
        assert revoke_resp.status_code == 204

        # Mint a third share token then soft-delete the model behind it
        created_soft = c.post(
            "/api/admin/share",
            json={"model_id": str(model_soft_id), "expires_in_hours": 1},
        )
        assert created_soft.status_code in (200, 201)
        token_soft_deleted = created_soft.json()["token"]
        with Session(engine) as s:
            m = s.exec(select(Model).where(Model.id == model_soft_id)).first()
            m.deleted_at = datetime.datetime.now(datetime.UTC)
            s.add(m)
            s.commit()

        c.cookies.delete(ACCESS_COOKIE)

        ids = {
            "model_a": model_a_id,
            "model_b": model_b_id,
            "img_a": img_a_id,
            "stl_a": stl_a_id,
            "src_a": src_a_id,
            "img_b": img_b_id,
            "model_soft": model_soft_id,
            "soft_img": soft_img_id,
            "token_revoked": token_to_revoke,
            "token_soft_deleted": token_soft_deleted,
            "member_jwt": member_jwt,
        }
        yield c, token_valid, ids

    get_settings.cache_clear()
    get_engine.cache_clear()


# ===========================================================================
# IDOR matrix (12 tests, Codex-mandated per SCP §3.4.2 + Story 11.2 acceptance)
# ===========================================================================


def test_anon_valid_token_valid_file_returns_200(share_fixture):
    c, token, ids = share_fixture
    r = c.get(f"/api/share/{token}/files/{ids['img_a']}/content")
    assert r.status_code == 200, r.text
    assert r.content == b"IMG_A"


def test_anon_valid_token_wrong_model_file_returns_404(share_fixture):
    c, token, ids = share_fixture
    # token resolves model_a; img_b belongs to model_b → uniform 404
    r = c.get(f"/api/share/{token}/files/{ids['img_b']}/content")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_anon_valid_token_non_shareable_kind_returns_404(share_fixture):
    c, token, ids = share_fixture
    # src_a kind=source belongs to model_a but is NOT in {image, print, stl}
    r = c.get(f"/api/share/{token}/files/{ids['src_a']}/content")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_anon_revoked_token_returns_404(share_fixture):
    c, _token, ids = share_fixture
    r = c.get(f"/api/share/{ids['token_revoked']}/files/{ids['img_a']}/content")
    assert r.status_code == 404


def test_anon_soft_deleted_model_returns_404(share_fixture):
    c, _token, ids = share_fixture
    # token resolves model_soft, which is now soft-deleted
    r = c.get(f"/api/share/{ids['token_soft_deleted']}/files/{ids['soft_img']}/content")
    assert r.status_code == 404


def test_anon_garbage_token_returns_404_with_fail_audit(share_fixture):
    """Token-resolve-failure path emits share.asset.fail audit.

    Codex P2-1 (2026-05-20) — brute-force / revoked-token-reuse attempts
    MUST be auditable. Pre-fix this code path raised 404 without emitting
    any audit row → NFR6-OBS-1 silent on the most-attacker-relevant surface.
    """
    c, _token, _ids = share_fixture
    bogus_token = "garbage-token-does-not-exist-anywhere"
    bogus_file = "00000000-0000-0000-0000-000000000000"
    r = c.get(f"/api/share/{bogus_token}/files/{bogus_file}/content")
    assert r.status_code == 404

    engine = get_engine()
    with Session(engine) as s:
        row = s.exec(
            select(AuditLog)
            .where(AuditLog.action == "share.asset.fail")
            .order_by(AuditLog.at.desc())
        ).first()
        assert row is not None
        assert "token_resolve_failed" in (row.after_json or "")
        # Token-hash present; clear token MUST NOT be in audit payload
        expected_hash = hashlib.sha256(bogus_token.encode()).hexdigest()
        assert expected_hash in (row.after_json or "")
        assert bogus_token not in (row.after_json or "")


def test_anon_stl_kind_returns_200(share_fixture):
    c, token, ids = share_fixture
    r = c.get(f"/api/share/{token}/files/{ids['stl_a']}/content")
    assert r.status_code == 200
    assert r.content == b"STL_A"


def test_audit_row_present_on_success(share_fixture):
    c, token, ids = share_fixture
    r = c.get(f"/api/share/{token}/files/{ids['img_a']}/content")
    assert r.status_code == 200
    engine = get_engine()
    with Session(engine) as s:
        row = s.exec(
            select(AuditLog)
            .where(AuditLog.action == "share.asset.fetched")
            .order_by(AuditLog.at.desc())
        ).first()
        assert row is not None
        assert row.entity_type == "share_token"
        assert row.actor_user_id is None
        # Token-hash present; clear token MUST NOT be in audit payload
        expected_hash = hashlib.sha256(token.encode()).hexdigest()
        assert expected_hash in (row.after_json or "")
        assert token not in (row.after_json or "")


def test_audit_row_present_on_fail(share_fixture):
    c, token, ids = share_fixture
    # Wrong-model failure → emit share.asset.fail
    c.get(f"/api/share/{token}/files/{ids['img_b']}/content")
    engine = get_engine()
    with Session(engine) as s:
        row = s.exec(
            select(AuditLog)
            .where(AuditLog.action == "share.asset.fail")
            .order_by(AuditLog.at.desc())
        ).first()
        assert row is not None
        assert row.entity_type == "share_token"
        assert "scope_check_failed" in (row.after_json or "")
        # Token NEVER in fail audit payload
        assert token not in (row.after_json or "")


def test_cache_control_no_store_and_no_validators(share_fixture):
    """Decision N hardening contract: no cache validators on share-asset
    responses. Cache-Control: no-store + absence of ETag + Last-Modified
    headers ensures downstream caches cannot treat the response as cacheable
    and cannot revalidate via If-None-Match / If-Modified-Since (which
    would round-trip back to the handler for a fresh scope check anyway,
    but stripping the validators eliminates the ambiguity entirely).
    Codex P2-2 followup (2026-05-20) — FileResponse populates validators
    in __call__ unless stat_result is passed to the constructor.
    """
    c, token, ids = share_fixture
    r = c.get(f"/api/share/{token}/files/{ids['img_a']}/content")
    assert r.status_code == 200
    assert "no-store" in r.headers.get("cache-control", "").lower()
    header_keys = {k.lower() for k in r.headers}
    assert "etag" not in header_keys, f"ETag present: {r.headers.get('etag')}"
    last_modified = r.headers.get("last-modified")
    assert "last-modified" not in header_keys, f"Last-Modified present: {last_modified}"


def test_scope_check_survives_if_none_match_after_revoke(share_fixture):
    """ETag/304 cache-revalidation MUST NOT bypass the scope check.

    Codex peer-grill (SCP §3.4.2 hardening #4) flagged the ETag/304
    short-circuit hazard: if a client cached an ETag from a valid fetch
    and the token is subsequently revoked, an `If-None-Match` request
    must NOT return 304 — the handler must re-run the scope check first
    and return 404 instead. Starlette's FileResponse populates ETag +
    Last-Modified automatically, so the actual security property is
    "scope check runs before any cache short-circuit", not "no ETag in
    response".
    """
    c, token, ids = share_fixture

    # First fetch — valid token; capture ETag
    r1 = c.get(f"/api/share/{token}/files/{ids['img_a']}/content")
    assert r1.status_code == 200
    etag = r1.headers.get("etag")

    # Revoke the token
    c.cookies.set(ACCESS_COOKIE, ids["member_jwt"])  # member can't revoke
    # Use admin path via direct delete; need admin cookie. Easier: revoke via
    # the existing fixture's `token_revoked` is already revoked. Use that
    # token to verify the post-revoke behavior with If-None-Match.
    c.cookies.delete(ACCESS_COOKIE)
    revoked_token = ids["token_revoked"]
    r2 = c.get(
        f"/api/share/{revoked_token}/files/{ids['img_a']}/content",
        headers={"If-None-Match": etag} if etag else {},
    )
    # Scope check rejects revoked token → uniform 404 (NOT 304)
    assert r2.status_code == 404


def test_logging_redaction_path_token(share_fixture):
    """Path-bearer token MUST NOT appear in logged URLs.

    Verifies the new `_SHARE_PATH_TOKEN_REGEX` in logging.py redacts the
    bearer segment from any log record that contains `/api/share/<token>/...`
    OR `/share/<token>/...` (nginx access log shape). Without this redaction
    the token leaks via app log records (httpx HTTP request logger), OTel
    span attributes, error events.
    """
    from app.core.logging import TokenRedactionFilter

    flt = TokenRedactionFilter()
    log_record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname="x",
        lineno=1,
        msg=(
            f"HTTP Request: GET /api/share/{'a' * 32}/files/abc/content "
            f"AND /share/{'b' * 32} resolved"
        ),
        args=(),
        exc_info=None,
    )
    flt.filter(log_record)
    assert "a" * 32 not in log_record.msg
    assert "b" * 32 not in log_record.msg
    assert "/api/share/<redacted>/files/abc/content" in log_record.msg
    assert "/share/<redacted>" in log_record.msg


def test_download_flag_sets_filename_in_disposition(share_fixture):
    c, token, ids = share_fixture
    r_default = c.get(f"/api/share/{token}/files/{ids['stl_a']}/content")
    r_download = c.get(f"/api/share/{token}/files/{ids['stl_a']}/content?download=true")
    assert "content-disposition" not in {k.lower() for k in r_default.headers}
    assert "content-disposition" in {k.lower() for k in r_download.headers}
    assert "m.stl" in r_download.headers["content-disposition"]


# ===========================================================================
# Cross-validation against Story 11.1 default-deny posture (3 tests)
# ===========================================================================


def test_authenticated_member_models_files_content_returns_200(share_fixture):
    """Authenticated user can still reach legacy `/api/models/.../content` path
    (Story 11.1's `current_user` Depends; verified here to ensure cross-flow
    consistency — the share-scoped endpoint is the ADDITIONAL anonymous
    surface, not a replacement of the authenticated path).
    """
    c, _token, ids = share_fixture
    c.cookies.set(ACCESS_COOKIE, ids["member_jwt"])
    r = c.get(f"/api/models/{ids['model_a']}/files/{ids['img_a']}/content")
    assert r.status_code == 200
    assert r.content == b"IMG_A"
    c.cookies.delete(ACCESS_COOKIE)


def test_anon_models_files_content_returns_401(share_fixture):
    """Legacy /api/models/.../content path is 401 anonymous post-Story-11.1.
    Anonymous share-recipients MUST go through /api/share/... endpoint.
    """
    c, _token, ids = share_fixture
    r = c.get(f"/api/models/{ids['model_a']}/files/{ids['img_a']}/content")
    assert r.status_code == 401


def test_share_resolve_emits_share_scoped_urls(share_fixture):
    """Share-resolve emits `/api/share/{token}/files/{fid}/content` URLs.

    This is the mechanical test that WOULD HAVE CAUGHT hot-fix 64447ff at
    code-review time had it existed at the time (Codex's cognitive-pattern
    property check per SCP §3.4.2). Future commits that touch share-router
    URL emission can never silently regress to `/api/models/...` without
    failing this test.
    """
    c, token, _ids = share_fixture
    body = c.get(f"/api/share/{token}").json()
    expected_prefix = f"/api/share/{token}/files/"
    assert all(
        url.startswith(expected_prefix) for url in body["images"]
    ), f"images contain non-share-scoped URL: {body['images']}"
    assert body["thumbnail_url"].startswith(expected_prefix), body["thumbnail_url"]
    assert body["stl_url"].startswith(expected_prefix), body["stl_url"]
    # And explicitly NOT the legacy /api/models/... path
    for url in [*body["images"], body["thumbnail_url"], body["stl_url"]]:
        assert "/api/models/" not in url, f"legacy URL emitted: {url}"
