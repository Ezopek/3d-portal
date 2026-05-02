"""Make migrate_catalog_3mf.py importable from tests/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest
import trimesh


@pytest.fixture
def make_sphere():
    """Factory for a unit icosphere (642 faces by default)."""

    def _make(radius: float = 10.0, subdivisions: int = 2) -> trimesh.Trimesh:
        return trimesh.creation.icosphere(subdivisions=subdivisions, radius=radius)

    return _make


@pytest.fixture
def make_cube():
    """Factory for an axis-aligned box mesh (12 faces)."""

    def _make(extents=(10.0, 10.0, 10.0)) -> trimesh.Trimesh:
        return trimesh.creation.box(extents=extents)

    return _make


@pytest.fixture
def make_3mf(tmp_path):
    """Factory: write a 3mf file containing the given meshes.

    For one mesh: writes a single-body 3mf via mesh.export.
    For multiple meshes: builds a Scene and exports it as 3mf.
    """

    def _make(name: str, meshes: list) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if len(meshes) == 1:
            meshes[0].export(str(path), file_type="3mf")
        else:
            scene = trimesh.Scene()
            for i, m in enumerate(meshes):
                scene.add_geometry(m, geom_name=f"obj_{i+1}")
            scene.export(str(path), file_type="3mf")
        return path

    return _make
