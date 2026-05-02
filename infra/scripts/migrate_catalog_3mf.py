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


# === Constants ===

CATEGORIES = (
    "decorum",
    "drukarka_3d",
    "gridfinity",
    "multiboard",
    "narzedzia",
    "praktyczne",
    "premium",
    "inne",
)
ARCHIVE_REL = Path("_archive") / "3mf-originals"
WLASNE_DIR = "wlasne modele"
MOSFET_DIR = "mosfet_hw-700_case"
NARZEDZIA_DIR = "narzedzia"
WRAPPABLE_EXTS = {".stl", ".3mf", ".step", ".stp"}
SKIP_SUBDIRS = {"prints", "_archive"}


# === Scanner ===


def scan_catalog(root: Path) -> list:
    """Walk the catalog and produce an ordered Action list.

    Order invariants:
      - Wraps come before any Convert/Archive that operates on a wrapped path.
      - Within wlasne modele/, MoveDir/DeleteFile come before RemoveEmptyDir.
    """
    actions: list = []

    for category in CATEGORIES:
        cat_path = root / category
        if not cat_path.is_dir():
            continue

        for entry in sorted(cat_path.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_file():
                ext = entry.suffix.lower()
                if ext in WRAPPABLE_EXTS:
                    new_folder = cat_path / entry.stem
                    actions.append(WrapInFolder(file=entry, folder=new_folder))
                    if ext == ".3mf":
                        new_3mf = new_folder / entry.name
                        actions.append(Convert3mf(src=new_3mf))
                        actions.append(
                            Archive3mf(
                                src=new_3mf,
                                dst=_archive_path_for(new_3mf, root),
                            )
                        )
            elif entry.is_dir():
                for f3mf in _find_3mfs_in_model_folder(entry):
                    has_sibling_stl = any(
                        sib.is_file() and sib.suffix.lower() == ".stl"
                        for sib in f3mf.parent.iterdir()
                    )
                    if has_sibling_stl:
                        actions.append(
                            Archive3mf(
                                src=f3mf,
                                dst=_archive_path_for(f3mf, root),
                            )
                        )
                    else:
                        actions.append(Convert3mf(src=f3mf))
                        actions.append(
                            Archive3mf(
                                src=f3mf,
                                dst=_archive_path_for(f3mf, root),
                            )
                        )

    wlasne = root / WLASNE_DIR
    if wlasne.is_dir():
        for entry in sorted(wlasne.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir() and entry.name == MOSFET_DIR:
                actions.append(
                    MoveDir(src=entry, dst=root / NARZEDZIA_DIR / MOSFET_DIR)
                )
            elif entry.is_file():
                actions.append(DeleteFile(path=entry))
            elif entry.is_dir():
                # Unknown subdir under wlasne modele/; skip (surface as orphan in report).
                continue
        actions.append(RemoveEmptyDir(path=wlasne))

    return actions


def _find_3mfs_in_model_folder(folder: Path) -> list:
    """Recurse into a model folder, collecting 3mfs, skipping prints/ and _archive/."""
    out = []
    for entry in folder.iterdir():
        if entry.is_dir():
            if entry.name in SKIP_SUBDIRS:
                continue
            out.extend(_find_3mfs_in_model_folder(entry))
        elif entry.is_file() and entry.suffix.lower() == ".3mf":
            out.append(entry)
    return out


def _archive_path_for(src_3mf: Path, catalog_root: Path) -> Path:
    """Compute the archive destination preserving the catalog-relative path."""
    rel = src_3mf.relative_to(catalog_root)
    return catalog_root / ARCHIVE_REL / rel


# === Index updater ===

INDEX_DELETIONS = (
    "wlasne modele/podstawka_laptop_latitude_5450.FCStd",
    "wlasne modele/test_spiecia.FCStd",
)


def apply_index_updates(
    index: list[dict],
    actions: list,
    catalog_root: Path,
) -> list[dict]:
    """Return a new index list with paths/categories updated per actions.

    Mutations applied (in this order):
      1. Drop entries whose `path` matches INDEX_DELETIONS.
      2. For each MoveDir whose src matches an entry's `path`, update the
         entry's `path` (and `category` if mosfet → tools).
      3. For each WrapInFolder whose file matches an entry's `path`,
         update the entry's `path` to the new folder.
    """

    def rel(p: Path) -> str:
        return str(p.relative_to(catalog_root)).replace("\\", "/")

    new_index = [e for e in index if e["path"] not in INDEX_DELETIONS]

    for action in actions:
        if isinstance(action, MoveDir):
            src_rel = rel(action.src)
            dst_rel = rel(action.dst)
            for entry in new_index:
                if entry["path"] == src_rel:
                    entry["path"] = dst_rel
                    if action.dst.parts[-2] == NARZEDZIA_DIR:
                        entry["category"] = "tools"
        elif isinstance(action, WrapInFolder):
            src_rel = rel(action.file)
            dst_rel = rel(action.folder)
            for entry in new_index:
                if entry["path"] == src_rel:
                    entry["path"] = dst_rel

    return new_index
