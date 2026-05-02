"""Make migrate_catalog_3mf.py importable from tests/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
