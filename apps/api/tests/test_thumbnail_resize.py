import io
from pathlib import Path

import pytest
from PIL import Image

from app.modules.catalog.thumbnails import (
    ALLOWED_WIDTHS,
    InvalidWidthError,
    NotAnImageError,
    cache_path_for,
    resize_image,
)


def _png_bytes(size: tuple[int, int] = (1200, 800)) -> bytes:
    img = Image.new("RGB", size, color=(123, 200, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def src(tmp_path: Path) -> Path:
    p = tmp_path / "source.png"
    p.write_bytes(_png_bytes())
    return p


@pytest.fixture
def cache_root(tmp_path: Path) -> Path:
    return tmp_path / "thumb-cache"


def test_resize_produces_webp_at_requested_width(src, cache_root):
    out = resize_image(src, width=480, cache_root=cache_root)
    assert out.exists()
    assert out.suffix == ".webp"
    with Image.open(out) as img:
        assert img.format == "WEBP"
        assert img.width == 480


def test_resize_preserves_aspect_ratio(src, cache_root):
    out = resize_image(src, width=480, cache_root=cache_root)
    with Image.open(out) as img:
        # Source is 1200x800 (3:2); at width 480, height should be 320.
        assert img.width == 480
        assert img.height == 320


def test_resize_caches_and_reuses(src, cache_root):
    first = resize_image(src, width=480, cache_root=cache_root)
    first_mtime_ns = first.stat().st_mtime_ns
    second = resize_image(src, width=480, cache_root=cache_root)
    assert first == second
    # Second call must not rewrite the cache file.
    assert second.stat().st_mtime_ns == first_mtime_ns


def test_resize_busts_cache_when_source_mtime_changes(src, cache_root):
    first = resize_image(src, width=480, cache_root=cache_root)
    # Touch the source so its mtime advances; rewrite different content.
    src.write_bytes(_png_bytes(size=(800, 800)))
    second = resize_image(src, width=480, cache_root=cache_root)
    assert second != first  # different cache key — different file
    assert second.exists()
    with Image.open(second) as img:
        assert img.width == 480
        assert img.height == 480  # square source


def test_resize_rejects_unallowed_width(src, cache_root):
    with pytest.raises(InvalidWidthError):
        resize_image(src, width=999, cache_root=cache_root)


def test_resize_rejects_non_image(tmp_path, cache_root):
    txt = tmp_path / "notes.txt"
    txt.write_text("hello")
    with pytest.raises(NotAnImageError):
        resize_image(txt, width=480, cache_root=cache_root)


def test_allowed_widths_includes_card_sizes():
    assert {480, 960} <= set(ALLOWED_WIDTHS)


def test_cache_path_includes_width_and_mtime(src, cache_root):
    p1 = cache_path_for(src, 480, cache_root)
    p2 = cache_path_for(src, 960, cache_root)
    assert p1 != p2  # different widths → different keys
    src.write_bytes(_png_bytes(size=(2000, 2000)))
    p3 = cache_path_for(src, 480, cache_root)
    assert p3 != p1  # mtime change → different key
