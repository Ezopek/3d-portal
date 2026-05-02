"""Tests for convert_3mf_to_stls."""
import pytest
import trimesh

from migrate_catalog_3mf import convert_3mf_to_stls, ConversionError


def test_single_body_produces_one_unsuffixed_stl(make_3mf, make_sphere):
    src = make_3mf("widget.3mf", [make_sphere()])
    written = convert_3mf_to_stls(src)
    assert len(written) == 1
    assert written[0].name == "widget.stl"
    assert written[0].parent == src.parent
    assert written[0].exists()


def test_multi_body_produces_zero_padded_suffixes(make_3mf, make_sphere, make_cube):
    src = make_3mf("combo.3mf", [make_sphere(), make_cube()])
    written = convert_3mf_to_stls(src)
    assert len(written) == 2
    assert {p.name for p in written} == {"combo_01.stl", "combo_02.stl"}


def test_round_trip_preserves_face_count(make_3mf, make_sphere):
    sphere = make_sphere()
    src = make_3mf("rt.3mf", [sphere])
    [out] = convert_3mf_to_stls(src)
    reloaded = trimesh.load(str(out))
    assert isinstance(reloaded, trimesh.Trimesh)
    assert len(reloaded.faces) == len(sphere.faces)


def test_zero_triangle_mesh_raises_and_cleans_up(make_3mf, tmp_path):
    """A degenerate mesh fails validation; no STL is left behind."""
    empty = trimesh.Trimesh(vertices=[], faces=[])
    src = make_3mf("empty.3mf", [empty])
    with pytest.raises(ConversionError, match="0 triangles"):
        convert_3mf_to_stls(src)
    assert not (src.parent / "empty.stl").exists()


def test_existing_output_collision_raises(make_3mf, make_sphere):
    src = make_3mf("clash.3mf", [make_sphere()])
    pre_existing = src.parent / "clash.stl"
    pre_existing.write_text("placeholder")
    with pytest.raises(ConversionError, match="already exists"):
        convert_3mf_to_stls(src)
    assert pre_existing.read_text() == "placeholder"


def test_three_objects_uses_two_digit_padding(make_3mf, make_sphere):
    src = make_3mf("trio.3mf", [make_sphere(), make_sphere(radius=5.0), make_sphere(radius=2.0)])
    written = convert_3mf_to_stls(src)
    assert {p.name for p in written} == {"trio_01.stl", "trio_02.stl", "trio_03.stl"}


def test_thirteen_objects_uses_two_digit_padding(make_3mf, make_sphere):
    """13 < 100 so 2-digit padding still suffices."""
    meshes = [make_sphere(radius=float(i + 1)) for i in range(13)]
    src = make_3mf("many.3mf", meshes)
    written = convert_3mf_to_stls(src)
    names = {p.name for p in written}
    assert "many_01.stl" in names
    assert "many_13.stl" in names
    assert len(names) == 13
