"""PROFILE-PUBLISH-1 — admin publish/unpublish endpoint tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import AuditLog, Category, Model, ModelFile, ModelFileKind, User, UserRole
from app.main import _PUBLIC_ROUTES, create_app
from app.modules.slicer import profile_publish
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.profile_library import derive_block_id, store_block
from app.modules.slicer.profile_offer import (
    ProfileChain,
    build_offer_record,
    read_offer,
    store_offer,
)
from app.modules.slicer.profile_publish import PUBLISH_STATE_PUBLISHED, PUBLISH_STATE_UNPUBLISHED

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"
JWT_SECRET = "test"
ORCA_VERSION = "2.3.2"
STL_BYTES = b"solid profile-publish\nendsolid profile-publish\n"
STL_HASH = hashlib.sha256(STL_BYTES).hexdigest()


class _FakeArqPool:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def enqueue_job(self, name: str, *args: object, **kwargs: object) -> object:
        self.calls.append((name, args, kwargs))
        return object()


@pytest_asyncio.fixture
async def seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, Path, Path, uuid.UUID, _FakeArqPool]]:
    vendored_root = tmp_path / "vendored"
    content_dir = tmp_path / "content"
    system_dir = vendored_root / "system"
    system_dir.mkdir(parents=True)
    for source in (FIXTURES / "system").glob("*.json"):
        shutil.copy(source, system_dir / source.name)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")
    monkeypatch.setenv("PORTAL_CONTENT_DIR", str(content_dir))
    monkeypatch.setenv("SLICER_VENDORED_PROFILES_DIR", str(vendored_root))
    monkeypatch.setenv("SLICER_BUNDLE_STORE_DIR", str(tmp_path / "bundle-store"))
    monkeypatch.setenv("SLICER_ESTIMATE_STORE_DIR", str(tmp_path / "estimate-store"))
    monkeypatch.setenv("SLICER_STL_CACHE_DIR", str(tmp_path / "stl-cache"))
    monkeypatch.setenv("ORCA_VERSION", ORCA_VERSION)

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    engine = get_engine()
    init_schema(engine)

    with Session(engine) as session:
        admin = User(
            email="admin@localhost.localdomain",
            display_name="Admin",
            role=UserRole.admin,
            password_hash="x",
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        admin_id = admin.id
        _seed_stl_row(session, content_dir=content_dir)

    fake_redis = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake_redis)

    async def _aclose() -> None:
        return None

    factory.aclose = _aclose
    app.state.redis = factory
    pool = _FakeArqPool()
    app.state.arq = pool

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        yield ac, vendored_root, content_dir, admin_id, pool

    get_settings.cache_clear()
    get_engine.cache_clear()


def _seed_stl_row(session: Session, *, content_dir: Path) -> None:
    category = Category(slug=f"cat-{uuid.uuid4().hex[:8]}", name_en="cat")
    session.add(category)
    session.commit()
    session.refresh(category)
    model = Model(slug=f"model-{uuid.uuid4().hex[:8]}", name_en="m", category_id=category.id)
    session.add(model)
    session.commit()
    session.refresh(model)
    storage_path = f"models/{model.id}/files/part.stl"
    file_row = ModelFile(
        model_id=model.id,
        kind=ModelFileKind.stl,
        original_name="part.stl",
        storage_path=storage_path,
        sha256=STL_HASH,
        size_bytes=len(STL_BYTES),
        mime_type="model/stl",
    )
    session.add(file_row)
    session.commit()
    target = content_dir / storage_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(STL_BYTES)


def _token(role: str, subject: str | None = None) -> str:
    return encode_token(
        subject=subject or str(uuid.uuid4()), role=role, secret=JWT_SECRET, ttl_minutes=30
    )


async def _login_admin(ac: AsyncClient, admin_id: uuid.UUID) -> None:
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))


def _store_chain_block(
    root: Path,
    profile_type: str,
    block_id_name: str,
    body: dict,
    *,
    material_type: str | None = None,
) -> str:
    block_id = derive_block_id(profile_type, block_id_name)  # type: ignore[arg-type]
    manifest = {
        "manifest_version": "1",
        "block_id": block_id,
        "profile_type": profile_type,
        "name": block_id_name,
        "source": "user",
        "is_system": False,
        "inherit": body.get("inherit"),
        "inherit_chain": [body["inherit"]] if isinstance(body.get("inherit"), str) else [],
        "settings_id": None,
        "material_type": material_type,
        "compatible_printers": [],
        "validation_state": "usable",
        "reasons": [],
        "portal_label": None,
        "imported_at": "2026-06-06T00:00:00+00:00",
        "imported_by": "00000000-0000-0000-0000-0000000000aa",
        "original_filename": f"{profile_type}.json",
    }
    store_block(
        root,
        profile_type=profile_type,
        block_id=block_id,
        body=body,
        manifest=manifest,
    )  # type: ignore[arg-type]
    return block_id


def _seed_offer(root: Path, *, requires_attention: bool = False) -> str:
    partials = json.loads(
        (FIXTURES / "intents/creality-k1-max-microswiss-hf/TPU/standard.json").read_text(
            encoding="utf-8"
        )
    )
    machine = _store_chain_block(root, "machine", "offer-machine", partials["machine"])
    process = _store_chain_block(root, "process", "offer-process", partials["process"])
    filament = _store_chain_block(
        root,
        "filament",
        "offer-filament",
        partials["filament"],
        material_type="TPU",
    )
    offer_id = uuid.uuid4().hex
    record = build_offer_record(
        offer_id=offer_id,
        label="Standard",
        description=None,
        chain=ProfileChain(
            machine_block_id=machine,
            process_block_id=process,
            filament_block_id=filament,
        ),
        visibility="hidden" if requires_attention else "visible",
        is_default=requires_attention,
        compatible_material_categories=["TPU"],
        validation_state="usable",
        reasons=[],
        created_at="2026-06-06T00:00:00+00:00",
        created_by=uuid.UUID("00000000-0000-0000-0000-0000000000aa"),
        updated_at="2026-06-06T00:00:00+00:00",
    )
    store_offer(root, record)
    return offer_id


def test_publish_routes_not_public_allowlist() -> None:
    assert "/api/admin/profiles/offers/{offer_id}/publish" not in _PUBLIC_ROUTES
    assert "/api/admin/profiles/offers/{offer_id}/unpublish" not in _PUBLIC_ROUTES


@pytest.mark.asyncio
async def test_publish_requires_admin(seam) -> None:
    ac, root, _content_dir, _admin_id, _pool = seam
    offer_id = _seed_offer(root)
    ac.cookies.set("portal_access", _token("member"))

    r = await ac.post(f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": STL_HASH})

    assert r.status_code == 403


@pytest.mark.asyncio
async def test_publish_resolves_persists_enqueues_updates_sidecar_and_audits(seam) -> None:
    ac, root, _content_dir, admin_id, pool = seam
    await _login_admin(ac, admin_id)
    offer_id = _seed_offer(root)
    system_before = {
        p.relative_to(root).as_posix(): p.read_bytes() for p in (root / "system").rglob("*.json")
    }

    r = await ac.post(f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": STL_HASH})

    assert r.status_code == 200, r.text
    body = r.json()
    bundle_hash = body["published_bundle_hash"]
    assert len(bundle_hash) == 64
    assert body["publish_state"] == PUBLISH_STATE_PUBLISHED
    assert body["estimate_job_id"] == f"slice:{STL_HASH}:{bundle_hash}"
    assert body["estimate"] is None
    assert len(pool.calls) == 1
    job_name, args, kwargs = pool.calls[0]
    assert job_name == "slice_estimate"
    assert args == (STL_HASH, bundle_hash)
    assert kwargs["_job_id"] == f"slice:{STL_HASH}:{bundle_hash}"
    assert kwargs["_queue_name"] == "arq:slicer"
    assert BundleStore(root.parent / "bundle-store").has_bundle(bundle_hash)
    assert not (root / "intents").exists()
    assert {
        p.relative_to(root).as_posix(): p.read_bytes() for p in (root / "system").rglob("*.json")
    } == system_before

    sidecar = read_offer(root, offer_id)
    assert sidecar is not None
    assert sidecar["offer_manifest_version"] == "2"
    assert sidecar["publish_state"] == PUBLISH_STATE_PUBLISHED
    assert sidecar["published_bundle_hash"] == bundle_hash
    assert sidecar["published_by"] == str(admin_id)
    assert sidecar["published_stl_hash"] == STL_HASH

    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        [event] = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.offer_publish")
        ).all()
    assert event.entity_type == "slicer_profile"
    assert event.entity_id == uuid.UUID(offer_id)
    assert event.actor_user_id == admin_id
    after = json.loads(event.after_json)
    assert after["published_bundle_hash"] == bundle_hash
    assert after["designated_stl_hash"] == STL_HASH
    assert "machine_block_id" in after
    assert "gcode" not in event.after_json
    assert "/mnt/" not in event.after_json


@pytest.mark.asyncio
async def test_publish_blocks_requires_attention_without_sidecar_publish(seam) -> None:
    ac, root, _content_dir, admin_id, pool = seam
    await _login_admin(ac, admin_id)
    offer_id = _seed_offer(root, requires_attention=True)

    r = await ac.post(f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": STL_HASH})

    assert r.status_code == 409
    assert r.json()["detail"]["reason_category"] == "offer_requires_attention"
    sidecar = read_offer(root, offer_id)
    assert sidecar is not None
    assert sidecar.get("publish_state", PUBLISH_STATE_UNPUBLISHED) == PUBLISH_STATE_UNPUBLISHED
    assert pool.calls == []


@pytest.mark.asyncio
async def test_publish_sidecar_store_failure_does_not_enqueue(
    seam, monkeypatch: pytest.MonkeyPatch
) -> None:
    ac, root, _content_dir, admin_id, pool = seam
    await _login_admin(ac, admin_id)
    offer_id = _seed_offer(root)
    before = read_offer(root, offer_id)
    assert before is not None

    def fail_store(_root: Path | str, _sidecar: dict) -> Path:
        raise OSError("sidecar disk full")

    monkeypatch.setattr(profile_publish, "store_publish_state", fail_store)

    with pytest.raises(OSError, match="sidecar disk full"):
        await ac.post(f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": STL_HASH})

    assert pool.calls == []
    assert read_offer(root, offer_id) == before


@pytest.mark.asyncio
async def test_publish_rejects_absent_and_bad_offer_ids(seam) -> None:
    ac, _root, _content_dir, admin_id, _pool = seam
    await _login_admin(ac, admin_id)

    bad = await ac.post("/api/admin/profiles/offers/nothex/publish", json={"stl_hash": STL_HASH})
    missing = await ac.post(
        f"/api/admin/profiles/offers/{'0' * 32}/publish", json={"stl_hash": STL_HASH}
    )

    assert bad.status_code == 404
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_unpublish_is_idempotent_and_keeps_append_only_bundle(seam) -> None:
    ac, root, _content_dir, admin_id, _pool = seam
    await _login_admin(ac, admin_id)
    offer_id = _seed_offer(root)
    published = (
        await ac.post(f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": STL_HASH})
    ).json()
    bundle_hash = published["published_bundle_hash"]

    first = await ac.post(f"/api/admin/profiles/offers/{offer_id}/unpublish")
    second = await ac.post(f"/api/admin/profiles/offers/{offer_id}/unpublish")

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["publish_state"] == PUBLISH_STATE_UNPUBLISHED
    sidecar = read_offer(root, offer_id)
    assert sidecar is not None
    assert sidecar["publish_state"] == PUBLISH_STATE_UNPUBLISHED
    assert sidecar["published_bundle_hash"] is None
    assert BundleStore(root.parent / "bundle-store").has_bundle(bundle_hash)

    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        events = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.offer_unpublish")
        ).all()
    assert len(events) == 2
    assert all(e.entity_id == uuid.UUID(offer_id) for e in events)


# ---------------------------------------------------------------------------
# Story 35.6 — offer-publish matrix hook (AC-9)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_matrix_hook_calls_enumerate_matrix_cells(seam, monkeypatch) -> None:
    """AC-9 (35.6): successful publish triggers enumerate_matrix_cells for the published offer."""
    enumerate_calls: list = []

    def _fake_enumerate(offers, policy):
        enumerate_calls.extend(offers)
        return []

    monkeypatch.setattr(
        "app.modules.slicer.matrix_backfill.enumerate_matrix_cells",
        _fake_enumerate,
    )

    ac, root, _content_dir, admin_id, _pool = seam
    await _login_admin(ac, admin_id)
    offer_id = _seed_offer(root)

    r = await ac.post(f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": STL_HASH})

    assert r.status_code == 200, r.text
    assert len(enumerate_calls) >= 1, (
        "enumerate_matrix_cells must receive the published offer's sidecar"
    )
    assert enumerate_calls[0].get("offer_id") == offer_id


@pytest.mark.asyncio
async def test_publish_matrix_hook_exception_does_not_roll_back_publish(seam, monkeypatch) -> None:
    """AC-9 (35.6): a hook exception is swallowed — publish response must still be 200."""

    def _raise(*args, **kwargs):
        raise RuntimeError("matrix hook exploded")

    monkeypatch.setattr(
        "app.modules.slicer.matrix_backfill.enumerate_matrix_cells",
        _raise,
    )

    ac, root, _content_dir, admin_id, _pool = seam
    await _login_admin(ac, admin_id)
    offer_id = _seed_offer(root)

    r = await ac.post(f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": STL_HASH})

    assert r.status_code == 200, r.text
    assert r.json()["publish_state"] == PUBLISH_STATE_PUBLISHED
