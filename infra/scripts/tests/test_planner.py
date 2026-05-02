"""Tests for plan_migration and render_plan_markdown."""
from pathlib import Path

from migrate_catalog_3mf import (
    plan_migration,
    render_plan_markdown,
    Plan,
    WrapInFolder,
    Convert3mf,
    Archive3mf,
    DeleteFile,
    RemoveEmptyDir,
)


def test_empty_actions_produces_empty_plan(tmp_path):
    plan = plan_migration([], [], tmp_path)
    assert isinstance(plan, Plan)
    assert plan.actions == []
    assert plan.validations == []


def test_plan_carries_actions(tmp_path):
    actions = [
        WrapInFolder(
            file=tmp_path / "decorum" / "x.stl",
            folder=tmp_path / "decorum" / "x",
        )
    ]
    plan = plan_migration(actions, [], tmp_path)
    assert plan.actions == actions


def test_wrap_collision_surfaces_validation(tmp_path):
    """If <category>/<basename>/ already exists as a directory, that's a collision."""
    (tmp_path / "decorum" / "x").mkdir(parents=True)
    (tmp_path / "decorum" / "x.stl").write_text("dummy")
    actions = [
        WrapInFolder(
            file=tmp_path / "decorum" / "x.stl",
            folder=tmp_path / "decorum" / "x",
        )
    ]
    plan = plan_migration(actions, [], tmp_path)
    issues = [v for v in plan.validations if "collision" in v.lower()]
    assert len(issues) >= 1


def test_index_orphan_after_wrap_is_not_an_error(tmp_path):
    actions = [
        WrapInFolder(
            file=tmp_path / "decorum" / "x.stl",
            folder=tmp_path / "decorum" / "x",
        )
    ]
    index = [{"id": "001", "path": "decorum/x.stl", "category": "decorations"}]
    plan = plan_migration(actions, index, tmp_path)
    orphans = [v for v in plan.validations if "orphan" in v.lower()]
    assert orphans == []


def test_index_orphan_with_no_action_is_reported(tmp_path):
    """Index entry pointing at decorum/Z, no action references Z, Z does not exist → orphan."""
    index = [{"id": "010", "path": "decorum/Z", "category": "decorations"}]
    plan = plan_migration([], index, tmp_path)
    orphans = [v for v in plan.validations if "decorum/Z" in v]
    assert len(orphans) == 1


def test_render_plan_markdown_has_required_sections(tmp_path):
    actions = [
        WrapInFolder(
            file=tmp_path / "decorum" / "x.stl",
            folder=tmp_path / "decorum" / "x",
        ),
        Convert3mf(src=tmp_path / "decorum" / "y" / "y.3mf"),
        Archive3mf(
            src=tmp_path / "decorum" / "y" / "y.3mf",
            dst=tmp_path / "_archive" / "3mf-originals" / "decorum" / "y" / "y.3mf",
        ),
        DeleteFile(path=tmp_path / "wlasne modele" / "x.FCStd"),
        RemoveEmptyDir(path=tmp_path / "wlasne modele"),
    ]
    plan = plan_migration(actions, [], tmp_path)
    md = render_plan_markdown(plan)
    assert "## Wraps" in md
    assert "## Conversions" in md
    assert "## Archives" in md
    assert "## Deletions" in md
    assert "## Summary" in md
