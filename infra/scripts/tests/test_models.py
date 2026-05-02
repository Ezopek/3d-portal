"""Tests for Action dataclasses in migrate_catalog_3mf."""
from pathlib import Path

from migrate_catalog_3mf import (
    WrapInFolder,
    MoveDir,
    Convert3mf,
    Archive3mf,
    DeleteFile,
    RemoveEmptyDir,
)


def test_wrap_in_folder_carries_file_and_folder():
    a = WrapInFolder(file=Path("/cat/foo.stl"), folder=Path("/cat/foo"))
    assert a.file == Path("/cat/foo.stl")
    assert a.folder == Path("/cat/foo")


def test_actions_are_frozen_and_hashable():
    a = WrapInFolder(file=Path("/x"), folder=Path("/y"))
    {a}  # must be hashable


def test_actions_compare_by_value():
    a1 = MoveDir(src=Path("/a"), dst=Path("/b"))
    a2 = MoveDir(src=Path("/a"), dst=Path("/b"))
    assert a1 == a2


def test_convert3mf_carries_src():
    a = Convert3mf(src=Path("/cat/model/foo.3mf"))
    assert a.src.name == "foo.3mf"


def test_archive3mf_carries_src_and_dst():
    a = Archive3mf(
        src=Path("/cat/model/foo.3mf"),
        dst=Path("/cat/_archive/3mf-originals/cat/model/foo.3mf"),
    )
    assert a.src != a.dst


def test_delete_and_remove_empty_dir():
    DeleteFile(path=Path("/x.fcstd"))
    RemoveEmptyDir(path=Path("/wlasne modele"))
