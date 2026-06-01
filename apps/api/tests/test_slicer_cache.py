"""Tests for the content-hashed STL cache (Story 32.2, AC-4).

The worker reads STL bytes from a content-hashed cache at
``<root>/stl/<hash[:2]>/<hash>.stl`` — the same hash-prefix fan-out the render/STL
+ Story 32.1 bundle store use. The cache is populated API-side at enqueue by
copying the ``.190``-mirrored catalog STL; the worker ONLY reads (it never touches
an external/source host — OD-8 / NFR20-CONTAINER-1). A cache miss is a classified
``missing_stl`` failure at the worker, never a silent default.
"""

from __future__ import annotations

import hashlib
import inspect

import pytest

from app.modules.slicer.stl_cache import (
    StlCache,
    compute_stl_hash,
    is_content_hash,
    validate_content_hash,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_stl_cache_path_is_hash_fanout_layout(tmp_path):
    cache = StlCache(tmp_path)
    h = "ab" + "c" * 62
    p = cache.stl_path(h)
    assert p.parent.name == "ab"  # 2-char fan-out prefix
    assert p.parent.parent.name == "stl"
    assert p.name == f"{h}.stl"


def test_cache_miss_read_returns_none(tmp_path):
    cache = StlCache(tmp_path)
    assert cache.read_path("00" + "0" * 62) is None
    assert cache.has("00" + "0" * 62) is False


def test_populate_from_source_addresses_by_content_hash(tmp_path):
    cache = StlCache(tmp_path / "cache")
    src = tmp_path / "catalog.stl"
    data = b"solid cube\n... facets ...\nendsolid cube\n"
    src.write_bytes(data)

    stl_hash = cache.populate_from_source(src)

    assert stl_hash == _sha256_bytes(data)
    cached = cache.read_path(stl_hash)
    assert cached is not None
    assert cached == cache.stl_path(stl_hash)
    assert cached.read_bytes() == data
    assert cache.has(stl_hash) is True


def test_compute_stl_hash_matches_populate(tmp_path):
    src = tmp_path / "x.stl"
    src.write_bytes(b"mesh-bytes")
    cache = StlCache(tmp_path / "c")
    assert compute_stl_hash(src) == cache.populate_from_source(src)


def test_populate_is_idempotent_first_write_wins(tmp_path):
    cache = StlCache(tmp_path / "cache")
    src = tmp_path / "a.stl"
    src.write_bytes(b"same-bytes")
    h1 = cache.populate_from_source(src)
    # Re-populate the identical content: addressed path is unchanged, one file only.
    h2 = cache.populate_from_source(src)
    assert h1 == h2
    assert len(list((tmp_path / "cache" / "stl").rglob("*.stl"))) == 1


# --- review fix #2: content-hash validation is the path-traversal gate ----------


@pytest.mark.parametrize(
    "value,valid",
    [
        ("a" * 64, True),  # 64 lowercase hex
        ("0123456789abcdef" * 4, True),
        ("A" * 64, False),  # uppercase — project mints lowercase hexdigests
        ("g" * 64, False),  # non-hex char
        ("a" * 63, False),  # too short
        ("a" * 65, False),  # too long
        ("../../etc/passwd", False),  # separators / traversal
        ("ab/cd", False),
        ("", False),
        (None, False),
    ],
)
def test_is_content_hash_accepts_only_64_lowercase_hex(value, valid):
    assert is_content_hash(value) is valid


def test_validate_content_hash_raises_on_malformed():
    assert validate_content_hash("f" * 64) == "f" * 64
    with pytest.raises(ValueError, match="content hash"):
        validate_content_hash("../../etc/passwd")


def test_stl_path_refuses_to_build_path_from_malformed_hash(tmp_path):
    cache = StlCache(tmp_path)
    with pytest.raises(ValueError, match="content hash"):
        cache.stl_path("../../../etc/shadow")


def test_read_path_and_has_treat_malformed_hash_as_miss(tmp_path):
    cache = StlCache(tmp_path)
    assert cache.read_path("../../etc/passwd") is None
    assert cache.has("../../etc/passwd") is False
    assert cache.read_path("Z" * 64) is None


def test_read_path_takes_only_hash_no_external_source_path():
    # AC-4 (NFR20-CONTAINER-1 / OD-8): the worker's cache-read seam takes ONLY the
    # content hash — there is no parameter through which an external/source-host
    # path could be passed, so the worker structurally cannot read outside the cache.
    sig = inspect.signature(StlCache.read_path)
    params = [p for p in sig.parameters if p != "self"]
    assert params == ["stl_hash"]
    # The cache root is fixed at construction (a single settings-sourced dir).
    init_params = [p for p in inspect.signature(StlCache.__init__).parameters if p != "self"]
    assert init_params == ["root"]
