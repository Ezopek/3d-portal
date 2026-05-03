import pytest
import trimesh
from PIL import Image

from render.trimesh_render import VIEW_NAMES, _pack_meshes_xy, render_views


def test_renders_four_named_views_single_path(cube_stl, tmp_path):
    out = render_views(stl_paths=[cube_stl], output_dir=tmp_path, size=128)
    assert set(out.keys()) == set(VIEW_NAMES)
    assert set(VIEW_NAMES) == {"front", "side", "top", "iso"}


def test_each_view_is_png_with_expected_size(cube_stl, tmp_path):
    out = render_views(stl_paths=[cube_stl], output_dir=tmp_path, size=128)
    for path in out.values():
        assert path.exists()
        assert path.suffix == ".png"
        with Image.open(path) as img:
            assert img.format == "PNG"
            assert img.size == (128, 128)


def test_renders_four_named_views_multi_path(cube_stl, tmp_path):
    out = render_views(stl_paths=[cube_stl, cube_stl], output_dir=tmp_path, size=128)
    assert set(out.keys()) == set(VIEW_NAMES)
    for path in out.values():
        assert path.exists()


def test_pack_meshes_xy_combines_two_boxes_with_spacing(tmp_path):
    a = tmp_path / "a.stl"
    b = tmp_path / "b.stl"
    trimesh.creation.box(extents=[10, 10, 10]).export(a)
    trimesh.creation.box(extents=[10, 10, 10]).export(b)
    combined = _pack_meshes_xy([a, b], spacing_mm=5.0)
    # Two 10x10 boxes laid out on XY with 5 mm padding each → bounding box
    # in X or Y must be ≥ 2*10 (no overlap).
    assert combined.extents[0] >= 20.0 or combined.extents[1] >= 20.0


def test_pack_meshes_xy_preserves_total_face_count(tmp_path):
    a = tmp_path / "a.stl"
    b = tmp_path / "b.stl"
    trimesh.creation.box(extents=[10, 10, 10]).export(a)
    trimesh.creation.box(extents=[10, 10, 10]).export(b)
    combined = _pack_meshes_xy([a, b], spacing_mm=5.0)
    # Each box has 12 triangles; concatenated mesh should have 24.
    assert len(combined.faces) == 24


def test_pack_meshes_xy_raises_when_no_usable_meshes(tmp_path):
    bogus = tmp_path / "bogus.stl"
    bogus.write_bytes(b"not an stl")
    with pytest.raises((ValueError, Exception)):
        _pack_meshes_xy([bogus], spacing_mm=5.0)
