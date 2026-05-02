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
