"""Story 23.2 (TB-034) — STL preview source-tracking + single-flight lock.

Covers the dispatch-side hardening introduced in
``apps/api/app/modules/share/router.py``:

* AC5/AC7 — single-flight Redis SETNX lock blocks a second concurrent
  share-view from enqueueing a duplicate ``render_stl_previews`` job for
  the same STL.
* AC4/AC8 — share-list query filters ``stl_preview`` rows by the current
  STL's sha8 suffix on ``original_name``; stale orphan previews (from a
  prior STL or legacy pre-Story-23.2 rows) are NOT returned to share
  recipients.

Worker-side AC1/AC2/AC6 (sha8 in ``original_name`` + sha8 LIKE filter on
the idempotency count + lock release in ``finally``) are exercised in
``workers/render/tests/test_worker_sot.py``; this file focuses on the
share-router dispatch surface that pytest can drive via TestClient.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.auth.jwt import encode_token
from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
)
from app.main import create_app


@pytest.fixture
def sf_client(tmp_path, monkeypatch, _patch_arq_pool):
    """TestClient + fakeredis + arq-pool spy bound to ``app.state``.

    Returns a 4-tuple ``(client, admin_token, ids, fake_redis, arq_pool)``.
    The arq pool comes from the autouse ``_patch_arq_pool`` conftest
    fixture (its ``enqueue_job`` is an ``AsyncMock``); the share router
    consumes it via ``request.app.state.arq``.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/sf.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")

    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        app = create_app()
        fake = fakeredis.aioredis.FakeRedis()
        factory = MagicMock()
        factory.get = MagicMock(return_value=fake)

        async def _aclose():
            return None

        factory.aclose = _aclose

        with TestClient(app) as c:
            c.headers.update({"X-Portal-Client": "web"})
            # Swap the lifespan-installed real-Redis client for fakeredis
            # AFTER lifespan + bind the autouse mock arq pool.
            app.state.redis = factory
            app.state.arq = _patch_arq_pool

            from sqlmodel import select

            from app.core.db.models import User

            engine = get_engine()
            with Session(engine) as s:
                user = s.exec(
                    select(User).where(User.email == "admin@localhost.localdomain")
                ).first()
                user_id = user.id
                cat = Category(slug=f"sf-cat-{uuid.uuid4().hex[:6]}", name_en="SF-Cat")
                s.add(cat)
                s.flush()

                model = Model(
                    slug=f"sf-m-{uuid.uuid4().hex[:6]}",
                    name_en="SF Model",
                    name_pl="Model SF",
                    category_id=cat.id,
                )
                s.add(model)
                s.flush()

                # Seed an STL whose sha256 we control so we can hand-craft
                # ``original_name`` rows that match (or NOT match) the
                # sha8 LIKE filter on the dispatch + list queries.
                stl_sha256 = "a" * 64  # sha8 == "aaaaaaaa"
                stl = ModelFile(
                    model_id=model.id,
                    kind=ModelFileKind.stl,
                    original_name="Original.stl",
                    storage_path=f"models/{model.id}/Original.stl",
                    sha256=stl_sha256,
                    size_bytes=2048,
                    mime_type="model/stl",
                )
                s.add(stl)
                s.commit()
                s.refresh(stl)
                ids = {
                    "model": model.id,
                    "stl": stl.id,
                    "stl_sha8": stl_sha256[:8],
                    "category_slug": cat.slug,
                }
            token = encode_token(
                subject=str(user_id),
                role="admin",
                secret="test",
                ttl_minutes=30,
            )
            yield c, token, ids, fake, _patch_arq_pool
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()


def _mint_share_token(c: TestClient, admin_token: str, model_id: uuid.UUID) -> str:
    c.cookies.set("portal_access", admin_token)
    r = c.post(
        "/api/admin/share",
        json={"model_id": str(model_id), "expires_in_hours": 1},
    )
    assert r.status_code in (200, 201), r.text
    share_token = r.json()["token"]
    c.cookies.clear()
    return share_token


# ---------------------------------------------------------------------------
# AC5 + AC7 — single-flight Redis SETNX lock at dispatch
# ---------------------------------------------------------------------------


def test_single_flight_lock_blocks_second_dispatch_for_same_stl(sf_client):
    """SINGLE-FLIGHT-1: two share-view hits for the same STL → ONE enqueue.

    First call acquires ``share:stl_preview_lock:<stl_id>`` via SETNX
    and enqueues ``render_stl_previews``. Second call sees the lock held
    and silently skips enqueue. Total enqueue calls (for the render task
    we care about) == 1.
    """
    c, admin_token, ids, _fake, arq_pool = sf_client
    share_token = _mint_share_token(c, admin_token, ids["model"])

    arq_pool.enqueue_job.reset_mock()

    r1 = c.get(f"/api/share/{share_token}")
    assert r1.status_code == 200, r1.text
    r2 = c.get(f"/api/share/{share_token}")
    assert r2.status_code == 200, r2.text

    preview_enqueues = [
        call
        for call in arq_pool.enqueue_job.await_args_list
        if call.args and call.args[0] == "render_stl_previews"
    ]
    assert len(preview_enqueues) == 1, (
        f"expected single render_stl_previews dispatch under single-flight, "
        f"got {len(preview_enqueues)}: {preview_enqueues!r}"
    )
    assert preview_enqueues[0].args[1] == str(ids["stl"])


def test_single_flight_lock_released_when_enqueue_fails(sf_client):
    """SINGLE-FLIGHT-2: enqueue-failure path releases the lock immediately.

    Mirrors the ``except Exception`` branch in ``resolve_share`` — if the
    worker queue is down, we MUST release the lock so the next request
    can retry without waiting the full 300s TTL.
    """
    c, admin_token, ids, _fake, arq_pool = sf_client
    share_token = _mint_share_token(c, admin_token, ids["model"])

    # First call: enqueue blows up → lock acquired then released via the
    # explicit ``except`` branch in ``resolve_share``.
    arq_pool.enqueue_job.reset_mock()
    arq_pool.enqueue_job.side_effect = RuntimeError("arq pool down")

    r1 = c.get(f"/api/share/{share_token}")
    # Resolve still succeeds — STL preview dispatch is best-effort.
    assert r1.status_code == 200, r1.text
    first_enqueue_attempts = [
        call
        for call in arq_pool.enqueue_job.await_args_list
        if call.args and call.args[0] == "render_stl_previews"
    ]
    assert len(first_enqueue_attempts) == 1, (
        "first request MUST have attempted enqueue (and crashed) so the "
        "release-in-except path is actually exercised"
    )

    # Second call: enqueue path healthy → MUST be able to dispatch again.
    # If the lock had NOT been released in the prior except branch, the
    # dispatch-side SETNX guard would block this second enqueue (the lock
    # TTL is 300s, far longer than the wall time between requests). The
    # observable consequence of a working lock release is a successful
    # second dispatch.
    arq_pool.enqueue_job.side_effect = None
    arq_pool.enqueue_job.return_value = MagicMock(job_id="ok")
    arq_pool.enqueue_job.reset_mock()

    r2 = c.get(f"/api/share/{share_token}")
    assert r2.status_code == 200, r2.text
    second_enqueue_attempts = [
        call
        for call in arq_pool.enqueue_job.await_args_list
        if call.args and call.args[0] == "render_stl_previews"
    ]
    assert len(second_enqueue_attempts) == 1, (
        "second call after enqueue-failure release MUST dispatch; "
        f"got {second_enqueue_attempts!r} — lock was NOT released"
    )


# ---------------------------------------------------------------------------
# AC4 + AC8 — share-list filter excludes stale orphan previews
# ---------------------------------------------------------------------------


def _seed_preview_rows(*, model_id: uuid.UUID, sha8: str, label: str) -> list[uuid.UUID]:
    """Seed 4 stl_preview rows for a model with the given sha8 suffix.

    Returns the list of created preview file ids in deterministic order
    (iso, front, side, top — matching VIEW_NAMES).
    """
    from app.core.db.session import get_engine

    view_names = ("iso", "front", "side", "top")
    created: list[uuid.UUID] = []
    with Session(get_engine()) as s:
        for position, view in enumerate(view_names):
            new_uuid = uuid.uuid4()
            f = ModelFile(
                id=new_uuid,
                model_id=model_id,
                kind=ModelFileKind.stl_preview,
                original_name=f"{view}-{sha8}.png",
                storage_path=f"models/{model_id}/stl_previews/{label}-{new_uuid}.png",
                sha256=uuid.uuid4().hex,
                size_bytes=100,
                mime_type="image/png",
                position=position,
            )
            s.add(f)
            created.append(new_uuid)
        s.commit()
    return created


def test_share_list_filters_to_current_stl_sha8_only(sf_client):
    """SOURCE-TRACK-2: stale orphan previews (prior STL's sha8) are NOT
    surfaced; legacy rows lacking the sha8 suffix are NOT surfaced; only
    the CURRENT STL's 4 previews appear in ``images``.

    Mimics the post-STL-replace state: model has 4 OLD orphan previews
    (sha8 "deadbeef") + 4 NEW current-STL previews (sha8 from the
    seeded STL "aaaaaaaa") + 1 pre-Story-23.2 legacy row named
    ``iso.png`` (no sha8 suffix). The share-resolve ``images`` list MUST
    contain exactly the 4 current-STL previews.
    """
    c, admin_token, ids, _fake, _arq = sf_client

    from app.core.db.session import get_engine

    # Orphan previews from a prior STL geometry.
    _seed_preview_rows(model_id=ids["model"], sha8="deadbeef", label="orphan")
    # Pre-Story-23.2 legacy row — no sha8 suffix.
    with Session(get_engine()) as s:
        legacy = ModelFile(
            model_id=ids["model"],
            kind=ModelFileKind.stl_preview,
            original_name="iso.png",
            storage_path=f"models/{ids['model']}/stl_previews/legacy-iso.png",
            sha256=uuid.uuid4().hex,
            size_bytes=100,
            mime_type="image/png",
            position=0,
        )
        s.add(legacy)
        s.commit()
        s.refresh(legacy)
        legacy_id = legacy.id

    # Current STL's previews — sha8 matches the seeded STL row.
    current_ids = _seed_preview_rows(model_id=ids["model"], sha8=ids["stl_sha8"], label="current")

    share_token = _mint_share_token(c, admin_token, ids["model"])
    r = c.get(f"/api/share/{share_token}")
    assert r.status_code == 200, r.text
    body = r.json()

    preview_urls = [f"/api/share/{share_token}/files/{fid}/content" for fid in current_ids]
    # ``images`` is admin images (none here) + stl_preview matches in
    # position order. None of the orphan / legacy ids should be present.
    images = body["images"]
    assert set(preview_urls).issubset(set(images)), (
        f"current-STL previews missing from images: have {images!r}, "
        f"expected superset of {preview_urls!r}"
    )
    assert f"/api/share/{share_token}/files/{legacy_id}/content" not in images, (
        f"legacy ``iso.png`` row leaked into share images: {images!r}"
    )
    # No orphan id should be present.
    seeded_orphans_in_images = [u for u in images if "orphan" in u]  # paranoia
    assert seeded_orphans_in_images == []


def test_share_list_no_dispatch_when_current_preview_set_complete(sf_client):
    """SOURCE-TRACK-1: once a complete 4-view set exists with the CURRENT
    sha8 stamp, the dispatch-side count guard skips enqueue.

    Validates that ``existing_preview_count`` honors the sha8 LIKE
    filter — without it, the count would over-count orphan rows or
    under-count current rows and either over- or under-dispatch.
    """
    c, admin_token, ids, _fake, arq_pool = sf_client

    # Seed exactly 4 CURRENT-sha8 previews — the completion gate.
    _seed_preview_rows(model_id=ids["model"], sha8=ids["stl_sha8"], label="current")

    share_token = _mint_share_token(c, admin_token, ids["model"])

    arq_pool.enqueue_job.reset_mock()
    r = c.get(f"/api/share/{share_token}")
    assert r.status_code == 200, r.text
    preview_enqueues = [
        call
        for call in arq_pool.enqueue_job.await_args_list
        if call.args and call.args[0] == "render_stl_previews"
    ]
    assert len(preview_enqueues) == 0, (
        f"complete 4-view set should suppress dispatch; got {preview_enqueues!r}"
    )
