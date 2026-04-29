from PIL import Image

from render.trimesh_render import VIEW_NAMES, render_views


def test_renders_four_named_views(cube_stl, tmp_path):
    out = render_views(stl_path=cube_stl, output_dir=tmp_path, size=128)
    assert set(out.keys()) == set(VIEW_NAMES)
    assert set(VIEW_NAMES) == {"front", "side", "top", "iso"}


def test_each_view_is_png_with_expected_size(cube_stl, tmp_path):
    out = render_views(stl_path=cube_stl, output_dir=tmp_path, size=128)
    for view, path in out.items():
        assert path.exists()
        assert path.suffix == ".png"
        with Image.open(path) as img:
            assert img.format == "PNG"
            assert img.size == (128, 128)


def test_files_are_written_under_output_dir(cube_stl, tmp_path):
    out = render_views(stl_path=cube_stl, output_dir=tmp_path, size=128)
    for path in out.values():
        assert tmp_path in path.parents
