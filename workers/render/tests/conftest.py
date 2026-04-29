from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cube_stl() -> Path:
    return FIXTURES / "cube.stl"
