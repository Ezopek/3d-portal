"""Tests for the executor."""
from migrate_catalog_3mf import (
    execute,
    ExecutionResult,
    WrapInFolder,
    MoveDir,
    DeleteFile,
    RemoveEmptyDir,
    Archive3mf,
    Convert3mf,
)


def test_wrap_in_folder_moves_file_into_new_dir(tmp_path):
    cat = tmp_path / "decorum"
    cat.mkdir()
    f = cat / "x.stl"
    f.write_text("dummy")
    actions = [WrapInFolder(file=f, folder=cat / "x")]
    result = execute(actions, tmp_path)
    assert (cat / "x" / "x.stl").exists()
    assert not f.exists()
    assert result.completed == [actions[0]]


def test_move_dir_relocates_subtree(tmp_path):
    src = tmp_path / "wlasne modele" / "mosfet"
    src.mkdir(parents=True)
    (src / "Base.step").write_text("dummy")
    dst = tmp_path / "narzedzia" / "mosfet"
    actions = [MoveDir(src=src, dst=dst)]
    execute(actions, tmp_path)
    assert dst.is_dir()
    assert (dst / "Base.step").exists()
    assert not src.exists()


def test_delete_and_remove_empty_dir(tmp_path):
    d = tmp_path / "wlasne modele"
    d.mkdir()
    f = d / "x.FCStd"
    f.write_text("dummy")
    actions = [DeleteFile(path=f), RemoveEmptyDir(path=d)]
    execute(actions, tmp_path)
    assert not d.exists()


def test_archive_creates_destination_tree(tmp_path):
    src = tmp_path / "decorum" / "model" / "foo.3mf"
    src.parent.mkdir(parents=True)
    src.write_text("dummy")
    dst = tmp_path / "_archive" / "3mf-originals" / "decorum" / "model" / "foo.3mf"
    actions = [Archive3mf(src=src, dst=dst)]
    execute(actions, tmp_path)
    assert dst.exists()
    assert not src.exists()


def test_convert_failure_does_not_abort_other_actions(tmp_path, make_3mf, make_sphere):
    """A failing conversion lands in result.failed; subsequent actions still run."""
    ok_src = make_3mf("good.3mf", [make_sphere()])
    bogus_dir = tmp_path / "decorum" / "bad_model"
    bogus_dir.mkdir(parents=True)
    bogus = bogus_dir / "broken.3mf"
    bogus.write_text("not a real 3mf")  # trimesh will fail to load this

    other = tmp_path / "decorum" / "x.stl"
    (tmp_path / "decorum").mkdir(parents=True, exist_ok=True)
    other.write_text("dummy")

    actions = [
        Convert3mf(src=bogus),
        Convert3mf(src=ok_src),
        WrapInFolder(file=other, folder=tmp_path / "decorum" / "x"),
    ]
    result = execute(actions, tmp_path)
    assert any(a == actions[0] for a, _ in result.failed)
    assert actions[1] in result.completed
    assert actions[2] in result.completed


def test_dry_run_does_not_touch_disk(tmp_path):
    cat = tmp_path / "decorum"
    cat.mkdir()
    f = cat / "x.stl"
    f.write_text("dummy")
    actions = [WrapInFolder(file=f, folder=cat / "x")]
    result = execute(actions, tmp_path, dry_run=True)
    assert f.exists()
    assert not (cat / "x").exists()
    assert result.completed == []


def test_executor_aborts_on_wrap_into_existing_directory(tmp_path):
    cat = tmp_path / "decorum"
    cat.mkdir()
    f = cat / "x.stl"
    f.write_text("dummy")
    (cat / "x").mkdir()
    actions = [WrapInFolder(file=f, folder=cat / "x")]
    result = execute(actions, tmp_path)
    assert any(a == actions[0] for a, _ in result.failed)
