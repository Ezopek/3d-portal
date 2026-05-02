"""Catalog 3MF → STL migration tool.

See docs/superpowers/specs/2026-05-02-catalog-3mf-to-stl-migration-design.md.

Usage:
    python migrate_catalog_3mf.py --dry-run                     # show plan
    python migrate_catalog_3mf.py --apply                       # do migration
    python migrate_catalog_3mf.py --convert PATH/file.3mf       # one-off
    python migrate_catalog_3mf.py --catalog-root PATH ...       # override
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# === Action dataclasses ===


@dataclass(frozen=True)
class WrapInFolder:
    """Wrap a loose file in a per-model folder of the same basename."""

    file: Path
    folder: Path


@dataclass(frozen=True)
class MoveDir:
    """Move a directory tree (used for mosfet relocation)."""

    src: Path
    dst: Path


@dataclass(frozen=True)
class Convert3mf:
    """Convert a 3MF in place to per-object STL(s) in the same directory."""

    src: Path


@dataclass(frozen=True)
class Archive3mf:
    """Move a 3MF to _archive/3mf-originals/ preserving the catalog-relative path."""

    src: Path
    dst: Path


@dataclass(frozen=True)
class DeleteFile:
    """Permanently delete a file (used for FCStd / FCBak / test_spiecia.3mf)."""

    path: Path


@dataclass(frozen=True)
class RemoveEmptyDir:
    """Remove a directory that is expected to be empty after preceding actions."""

    path: Path


class ConversionError(Exception):
    """Raised when 3MF→STL conversion fails validation."""


class MigrationError(Exception):
    """Raised for fatal pre-flight errors (e.g. malformed index.json)."""


# === Converter ===

import trimesh  # noqa: E402  (placed after dataclasses to keep ordering readable)


def convert_3mf_to_stls(src: Path) -> list[Path]:
    """Convert a 3MF to per-object STLs in the same directory.

    Returns the list of created STL paths (in the order objects appear
    in the source). On any validation failure, raises ConversionError
    after removing any STLs already written for this 3MF (atomic).
    """
    loaded = trimesh.load(str(src))
    if isinstance(loaded, trimesh.Trimesh):
        meshes: list[tuple[str, trimesh.Trimesh]] = [(src.stem, loaded)]
    elif isinstance(loaded, trimesh.Scene):
        meshes = list(loaded.geometry.items())
    else:
        raise ConversionError(
            f"unknown loaded type from {src.name}: {type(loaded).__name__}"
        )

    n = len(meshes)
    if n == 0:
        raise ConversionError(f"{src.name} contains no meshes")
    width = max(2, len(str(n)))
    base = src.stem

    written: list[Path] = []
    try:
        for idx, (name, mesh) in enumerate(meshes, start=1):
            if not isinstance(mesh, trimesh.Trimesh):
                raise ConversionError(
                    f"{src.name} object {name!r} is not a Trimesh "
                    f"({type(mesh).__name__})"
                )
            try:
                mesh.fix_normals()
            except Exception:
                # Non-fatal — explicit triangle/bbox checks gate validity.
                pass
            if len(mesh.faces) == 0:
                raise ConversionError(
                    f"{src.name} object {name!r} has 0 triangles"
                )
            extent = mesh.bounds[1] - mesh.bounds[0]
            if not all(s > 0 for s in extent):
                raise ConversionError(
                    f"{src.name} object {name!r} has zero extent: "
                    f"{extent.tolist()}"
                )

            if n == 1:
                out_name = f"{base}.stl"
            else:
                out_name = f"{base}_{idx:0{width}d}.stl"
            out_path = src.parent / out_name
            if out_path.exists():
                raise ConversionError(
                    f"output {out_path.name} already exists in {src.parent}"
                )

            mesh.export(str(out_path), file_type="stl")

            reloaded = trimesh.load(str(out_path))
            if not isinstance(reloaded, trimesh.Trimesh):
                raise ConversionError(
                    f"round-trip of {out_path.name} loaded as "
                    f"{type(reloaded).__name__}, expected Trimesh"
                )
            if len(reloaded.faces) != len(mesh.faces):
                raise ConversionError(
                    f"round-trip face count mismatch for {out_path.name}: "
                    f"wrote {len(mesh.faces)}, read {len(reloaded.faces)}"
                )
            written.append(out_path)
    except Exception:
        for p in written:
            try:
                p.unlink()
            except FileNotFoundError:
                pass
        raise

    return written
