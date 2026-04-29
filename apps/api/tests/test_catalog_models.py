import pytest
from pydantic import ValidationError

from app.modules.catalog.models import Model, Print


def test_model_parses_canonical_entry():
    m = Model.model_validate({
        "id": "001",
        "name_en": "Dragon",
        "name_pl": "Smok",
        "path": "decorum/dragon",
        "category": "decorations",
        "subcategory": "articulated_figures",
        "tags": ["dragon", "smok"],
        "source": "printables",
        "printables_id": "12345",
        "thangs_id": None,
        "makerworld_id": None,
        "source_url": "https://printables.com/m/12345",
        "rating": 5,
        "status": "printed",
        "notes": "",
        "thumbnail": None,
        "date_added": "2026-04-12",
    })
    assert m.id == "001"
    assert m.prints == []  # default when missing


def test_model_parses_with_prints_array():
    m = Model.model_validate({
        "id": "002", "name_en": "Vase", "name_pl": "Wazon", "path": "decorum/vase",
        "category": "decorations", "subcategory": "", "tags": [], "source": "unknown",
        "printables_id": None, "thangs_id": None, "makerworld_id": None,
        "source_url": None, "rating": None, "status": "not_printed", "notes": "",
        "thumbnail": None, "date_added": "2026-04-29",
        "prints": [
            {
                "path": "decorum/vase/prints/2026-04-29-front.jpg",
                "date": "2026-04-29",
                "notes_en": "First", "notes_pl": "Pierwszy",
            },
        ],
    })
    assert len(m.prints) == 1
    assert m.prints[0].notes_pl == "Pierwszy"


def test_model_rejects_unknown_status():
    with pytest.raises(ValidationError):
        Model.model_validate({
            "id": "003", "name_en": "X", "name_pl": "X", "path": "x",
            "category": "decorations", "subcategory": "", "tags": [], "source": "unknown",
            "printables_id": None, "thangs_id": None, "makerworld_id": None,
            "source_url": None, "rating": None, "status": "garbage",
            "notes": "", "thumbnail": None, "date_added": "2026-04-29",
        })
