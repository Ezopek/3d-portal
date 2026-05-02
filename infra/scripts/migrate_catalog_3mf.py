"""Catalog 3MF → STL migration tool.

See docs/superpowers/specs/2026-05-02-catalog-3mf-to-stl-migration-design.md.

Usage:
    python migrate_catalog_3mf.py --dry-run                     # show plan
    python migrate_catalog_3mf.py --apply                       # do migration
    python migrate_catalog_3mf.py --convert PATH/file.3mf       # one-off
    python migrate_catalog_3mf.py --catalog-root PATH ...       # override
"""
from __future__ import annotations
