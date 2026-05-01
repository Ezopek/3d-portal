import hashlib
from pathlib import Path

from PIL import Image, UnidentifiedImageError

ALLOWED_WIDTHS: frozenset[int] = frozenset({240, 480, 720, 960, 1280})
IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp"})
_WEBP_QUALITY = 80
# WebP encoder effort. method=6 is max-compression but ~120x slower than method=4
# on RGBA inputs (the trimesh-generated 768x768 renders) — 1.9s vs 15ms per call.
# method=4 trades ~4% larger output for a usable cold-cache experience.
_WEBP_METHOD = 4
_THUMBS_SUBDIR = "thumbnails"


class InvalidWidthError(ValueError):
    """Width is not in the allowlist."""


class NotAnImageError(ValueError):
    """Source path does not point at a supported image."""


def cache_path_for(src: Path, width: int, cache_root: Path) -> Path:
    """Return the cache path for `src` resized to `width`.

    Key includes a sha1 of the absolute source path, the width, and the source
    mtime — when the source changes, the cache key changes automatically.
    """
    abs_src = src.resolve()
    mtime_ns = abs_src.stat().st_mtime_ns
    digest = hashlib.sha1(str(abs_src).encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
    return cache_root / _THUMBS_SUBDIR / f"{digest}_{width}_{mtime_ns}.webp"


def resize_image(src: Path, width: int, cache_root: Path) -> Path:
    """Return path to a WebP thumbnail of `src` at `width` px wide.

    Raises InvalidWidthError if `width` is not allowlisted, NotAnImageError if
    the source is not a supported image. Subsequent calls with the same source
    + width return the cached file without re-encoding.
    """
    if width not in ALLOWED_WIDTHS:
        raise InvalidWidthError(f"width {width} not in {sorted(ALLOWED_WIDTHS)}")
    if src.suffix.lower() not in IMAGE_EXTENSIONS:
        raise NotAnImageError(f"unsupported extension: {src.suffix}")

    out = cache_path_for(src, width, cache_root)
    if out.exists():
        return out

    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(src) as img:
            # Preserve transparency when present (renders may be transparent
            # PNGs); flatten palette images via RGBA so the WebP keeps alpha.
            if img.mode in ("P", "LA"):
                img = img.convert("RGBA")
            elif img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            img.thumbnail((width, width))
            img.save(out, format="WEBP", quality=_WEBP_QUALITY, method=_WEBP_METHOD)
    except UnidentifiedImageError as exc:
        raise NotAnImageError(f"cannot decode image: {src}") from exc
    return out
