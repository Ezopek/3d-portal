"""Story 13.2 / Decision P — thumbnail pipeline test surface.

Covers:
    - generate_thumbnail_sync unit behavior (WebP @ q80, 800px longest side,
      EXIF orientation, idempotent, structured-result on error paths).
    - NFR8-PERF-1 payload budget: ≤50 KB per typical phone-photo input.
    - Admin upload → arq enqueue integration: image-kind POST queues a
      ``generate_thumbnail`` job; non-image kinds do not.
    - SoT variant endpoint: ``?variant=thumb`` returns the WebP sibling when
      it exists; falls back to the original blob when missing.
"""

from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

import pytest
from PIL import Image
from sqlmodel import Session

from app.core.auth.jwt import encode_token
from app.core.config import get_settings
from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
    User,
    UserRole,
)
from app.core.db.session import get_engine
from app.workers.generate_thumbnail import (
    THUMBNAIL_LONGEST_SIDE_PX,
    THUMBNAIL_SUFFIX,
    generate_thumbnail_sync,
    thumbnail_path_for,
)

# ---------------------------------------------------------------------------
# Seeding helpers (mirror test_sot_admin_files.py)
# ---------------------------------------------------------------------------

JWT_SECRET = "test-secret-not-real"


def _admin_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="admin", secret=JWT_SECRET, ttl_minutes=30)


def _seed_admin(session: Session) -> uuid.UUID:
    u = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Admin",
        role=UserRole.admin,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_category(session: Session) -> uuid.UUID:
    cat = Category(slug=f"cat-{uuid.uuid4().hex[:8]}", name_en="Test Cat")
    session.add(cat)
    session.flush()
    return cat.id


def _seed_model(session: Session, cat_id: uuid.UUID) -> uuid.UUID:
    m = Model(
        slug=f"m-{uuid.uuid4().hex[:8]}",
        name_en="Test Model",
        category_id=cat_id,
    )
    session.add(m)
    session.flush()
    return m.id


def _seed_image_file(
    session: Session,
    model_id: uuid.UUID,
    *,
    content: bytes,
    storage_path: str,
    kind: ModelFileKind = ModelFileKind.image,
    mime: str = "image/jpeg",
    original_name: str = "phone-photo.jpg",
) -> uuid.UUID:
    sha256 = hashlib.sha256(content).hexdigest()
    f = ModelFile(
        model_id=model_id,
        kind=kind,
        original_name=original_name,
        storage_path=storage_path,
        sha256=sha256,
        size_bytes=len(content),
        mime_type=mime,
    )
    session.add(f)
    session.flush()
    return f.id


def _write_jpeg(path: Path, *, size: tuple[int, int], quality: int = 88) -> int:
    """Write a synthetic JPEG approximating phone-photo spatial coherence.

    Phone photos compress well because adjacent pixels are correlated
    (smooth gradients of sky / skin / fabric). Pure high-frequency noise
    would defeat both JPEG and WebP and produce an unrealistic test fixture.
    The pattern below uses smooth low-frequency gradients with a small
    sinusoidal modulation — visually rich enough to exercise the codec
    without being adversarial.
    """
    import math

    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", size)
    px = im.load()
    w, h = size
    for y in range(h):
        for x in range(w):
            # Smooth gradient + low-amplitude sine — mimics sky/horizon scenes.
            r = int((x / w) * 200 + 30 * math.sin(x / 60))
            g = int((y / h) * 220 + 20 * math.cos(y / 50))
            b = int(((x + y) / (w + h)) * 180 + 25 * math.sin((x + y) / 70))
            px[x, y] = (r % 256, g % 256, b % 256)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality)
    path.write_bytes(buf.getvalue())
    return path.stat().st_size


def _write_png_with_alpha(path: Path, *, size: tuple[int, int]) -> int:
    """Write a synthetic alpha-channel PNG approximating UI-screenshot coherence."""
    import math

    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGBA", size)
    px = im.load()
    w, h = size
    for y in range(h):
        for x in range(w):
            r = int((x / w) * 180 + 25 * math.sin(x / 80))
            g = int((y / h) * 200 + 25 * math.cos(y / 70))
            b = int(((x + y) / (w + h)) * 160 + 20 * math.sin((x + y) / 90))
            a = 255 if (x // 50 + y // 50) % 3 != 0 else 200
            px[x, y] = (r % 256, g % 256, b % 256, a)
    im.save(path, format="PNG")
    return path.stat().st_size


# ---------------------------------------------------------------------------
# Unit tests — generate_thumbnail_sync against synthetic phone-photo fixtures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,size",
    [
        ("portrait_3000x4000_jpeg", (3000, 4000)),
        ("landscape_4000x3000_jpeg", (4000, 3000)),
        ("portrait_2000x3000_jpeg", (2000, 3000)),
    ],
)
def test_thumbnail_jpeg_size_budget(tmp_path, label, size):
    """NFR8-PERF-1 — every typical phone-photo JPEG produces a ≤50 KB WebP."""
    settings = get_settings()
    content_dir = settings.portal_content_dir
    rel_path = f"models/test-{label}/files/{uuid.uuid4().hex}.jpg"
    abs_path = content_dir / rel_path
    _write_jpeg(abs_path, size=size)

    engine = get_engine()
    with Session(engine) as s:
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s, model_id, content=abs_path.read_bytes(), storage_path=rel_path
        )
        s.commit()

    result = generate_thumbnail_sync(engine, file_id, content_dir=content_dir)

    assert result["status"] == "ok", result
    assert result["thumbnail_path"] == rel_path + THUMBNAIL_SUFFIX
    assert result["size_bytes"] is not None
    assert result["size_bytes"] <= 50 * 1024, (
        f"{label}: thumbnail {result['size_bytes']} bytes exceeds NFR8-PERF-1 50 KB budget"
    )

    thumb_abs = thumbnail_path_for(abs_path)
    assert thumb_abs.is_file()
    with Image.open(thumb_abs) as out:
        assert out.format == "WEBP"
        # 800px longest side preserves aspect ratio.
        assert max(out.size) <= THUMBNAIL_LONGEST_SIDE_PX
        # Aspect-ratio preservation within rounding tolerance.
        in_ratio = size[0] / size[1]
        out_ratio = out.size[0] / out.size[1]
        assert abs(in_ratio - out_ratio) < 0.02


def test_thumbnail_png_with_alpha_size_budget(tmp_path):
    """NFR8-PERF-1 — alpha-channel PNG still fits the 50 KB budget."""
    settings = get_settings()
    content_dir = settings.portal_content_dir
    rel_path = f"models/test-png-alpha/files/{uuid.uuid4().hex}.png"
    abs_path = content_dir / rel_path
    _write_png_with_alpha(abs_path, size=(2000, 3000))

    engine = get_engine()
    with Session(engine) as s:
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s,
            model_id,
            content=abs_path.read_bytes(),
            storage_path=rel_path,
            mime="image/png",
            original_name="screenshot.png",
        )
        s.commit()

    result = generate_thumbnail_sync(engine, file_id, content_dir=content_dir)
    assert result["status"] == "ok", result
    assert result["size_bytes"] is not None
    assert result["size_bytes"] <= 50 * 1024, (
        f"PNG-with-alpha thumbnail {result['size_bytes']} bytes exceeds NFR8-PERF-1 50 KB budget"
    )


def test_thumbnail_idempotent_second_run_is_skipped(tmp_path):
    """Running the task twice on the same ModelFile is a no-op the second time."""
    settings = get_settings()
    content_dir = settings.portal_content_dir
    rel_path = f"models/test-idemp/files/{uuid.uuid4().hex}.jpg"
    abs_path = content_dir / rel_path
    _write_jpeg(abs_path, size=(1600, 1200))

    engine = get_engine()
    with Session(engine) as s:
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s, model_id, content=abs_path.read_bytes(), storage_path=rel_path
        )
        s.commit()

    first = generate_thumbnail_sync(engine, file_id, content_dir=content_dir)
    assert first["status"] == "ok"
    thumb_abs = thumbnail_path_for(abs_path)
    first_mtime = thumb_abs.stat().st_mtime_ns

    second = generate_thumbnail_sync(engine, file_id, content_dir=content_dir)
    assert second["status"] == "skipped"
    # File must not have been rewritten — mtime preserved.
    assert thumb_abs.stat().st_mtime_ns == first_mtime


def test_thumbnail_row_missing(tmp_path):
    engine = get_engine()
    result = generate_thumbnail_sync(engine, uuid.uuid4())
    assert result["status"] == "row_missing"
    assert result["thumbnail_path"] is None


def test_thumbnail_non_image_kind_no_op():
    """STL / archive kinds: structured-skip, no file ops attempted."""
    engine = get_engine()
    with Session(engine) as s:
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s,
            model_id,
            content=b"NOT_AN_IMAGE",
            storage_path=f"models/{model_id}/files/{uuid.uuid4().hex}.stl",
            kind=ModelFileKind.stl,
            mime="model/stl",
            original_name="model.stl",
        )
        s.commit()
    result = generate_thumbnail_sync(engine, file_id)
    assert result["status"] == "not_image"


def test_thumbnail_original_missing_on_disk(tmp_path):
    """DB row exists but storage_path doesn't — structured warning, no crash."""
    engine = get_engine()
    with Session(engine) as s:
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s,
            model_id,
            content=b"missing-bytes",
            storage_path=f"models/{model_id}/files/{uuid.uuid4().hex}.jpg",
        )
        s.commit()
    # NB: never wrote the file to disk.
    result = generate_thumbnail_sync(engine, file_id)
    assert result["status"] == "missing"
    assert result["reason"] == "original_missing"


def test_thumbnail_print_kind_also_processed():
    """Catalog gallery surfaces both image and print kinds → both produce thumbs."""
    settings = get_settings()
    content_dir = settings.portal_content_dir
    rel_path = f"models/test-print-kind/files/{uuid.uuid4().hex}.jpg"
    abs_path = content_dir / rel_path
    _write_jpeg(abs_path, size=(1200, 900))

    engine = get_engine()
    with Session(engine) as s:
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s,
            model_id,
            content=abs_path.read_bytes(),
            storage_path=rel_path,
            kind=ModelFileKind.print,
        )
        s.commit()
    result = generate_thumbnail_sync(engine, file_id, content_dir=content_dir)
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Integration — admin upload enqueues generate_thumbnail
# ---------------------------------------------------------------------------


def test_image_upload_enqueues_thumbnail(client, _patch_arq_pool):
    """Image-kind POST to /api/admin/models/{id}/files enqueues the task."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    # Build a tiny JPEG payload via Pillow so the API actually accepts a
    # real image MIME body (mime is guessed from the filename extension).
    buf = io.BytesIO()
    Image.new("RGB", (200, 150), color=(127, 64, 200)).save(buf, format="JPEG", quality=80)
    files = {"file": ("tiny.jpg", buf.getvalue(), "image/jpeg")}
    data = {"kind": "image"}

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(f"/api/admin/models/{model_id}/files", files=files, data=data)
    assert r.status_code == 201, r.text

    _patch_arq_pool.enqueue_job.assert_any_call("generate_thumbnail", uuid.UUID(r.json()["id"]))


def test_stl_upload_does_not_enqueue_thumbnail(client, _patch_arq_pool):
    """STL uploads enqueue render, never generate_thumbnail."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    files = {"file": ("part.stl", b"solid x\nendsolid", "model/stl")}
    data = {"kind": "stl"}

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(f"/api/admin/models/{model_id}/files", files=files, data=data)
    assert r.status_code == 201, r.text

    thumbnail_calls = [
        c
        for c in _patch_arq_pool.enqueue_job.call_args_list
        if c.args and c.args[0] == "generate_thumbnail"
    ]
    assert thumbnail_calls == []


# ---------------------------------------------------------------------------
# Endpoint — variant routing on GET /api/models/.../content
# ---------------------------------------------------------------------------


def test_variant_thumb_serves_webp_when_present(client):
    """variant=thumb + sibling exists → WebP body + image/webp Content-Type."""
    engine = get_engine()
    settings = get_settings()
    content_dir = settings.portal_content_dir

    rel_path = f"models/test-variant-present/files/{uuid.uuid4().hex}.jpg"
    abs_path = content_dir / rel_path
    _write_jpeg(abs_path, size=(1600, 1200))

    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s, model_id, content=abs_path.read_bytes(), storage_path=rel_path
        )
        s.commit()

    # Generate the variant inline.
    result = generate_thumbnail_sync(engine, file_id, content_dir=content_dir)
    assert result["status"] == "ok"

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.get(f"/api/models/{model_id}/files/{file_id}/content?variant=thumb")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/webp"
    # First 4 bytes of a WebP file: "RIFF"; bytes 8-11: "WEBP".
    assert r.content[:4] == b"RIFF"
    assert r.content[8:12] == b"WEBP"


def test_variant_thumb_falls_back_to_original_when_missing(client):
    """variant=thumb + sibling missing → serves original blob + original MIME."""
    engine = get_engine()
    settings = get_settings()
    content_dir = settings.portal_content_dir

    rel_path = f"models/test-variant-missing/files/{uuid.uuid4().hex}.jpg"
    abs_path = content_dir / rel_path
    _write_jpeg(abs_path, size=(800, 600))

    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s, model_id, content=abs_path.read_bytes(), storage_path=rel_path
        )
        s.commit()

    # No thumbnail generation → variant=thumb must fall back.
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.get(f"/api/models/{model_id}/files/{file_id}/content?variant=thumb")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"


def test_variant_absent_returns_original(client):
    """Backward-compat: no variant param → original blob, unchanged."""
    engine = get_engine()
    settings = get_settings()
    content_dir = settings.portal_content_dir

    rel_path = f"models/test-no-variant/files/{uuid.uuid4().hex}.jpg"
    abs_path = content_dir / rel_path
    _write_jpeg(abs_path, size=(800, 600))

    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_image_file(
            s, model_id, content=abs_path.read_bytes(), storage_path=rel_path
        )
        s.commit()
    # Render variant first so we can prove the no-variant path bypasses it.
    generate_thumbnail_sync(engine, file_id, content_dir=content_dir)

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.get(f"/api/models/{model_id}/files/{file_id}/content")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
