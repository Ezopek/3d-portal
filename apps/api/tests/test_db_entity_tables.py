from app.core.db.models import (
    ExternalSource,
    ModelFileKind,
    ModelSource,
    ModelStatus,
    NoteKind,
)


def test_model_source_enum_values():
    assert ModelSource.unknown.value == "unknown"
    assert ModelSource.printables.value == "printables"
    assert ModelSource.thangs.value == "thangs"
    assert ModelSource.makerworld.value == "makerworld"
    assert ModelSource.cults3d.value == "cults3d"
    assert ModelSource.thingiverse.value == "thingiverse"
    assert ModelSource.own.value == "own"
    assert ModelSource.other.value == "other"


def test_model_status_enum_values():
    assert {m.value for m in ModelStatus} == {
        "not_printed",
        "printed",
        "in_progress",
        "broken",
    }


def test_model_file_kind_enum_values():
    assert {m.value for m in ModelFileKind} == {
        "stl",
        "image",
        "print",
        "source",
        "archive_3mf",
    }


def test_external_source_enum_values():
    assert {m.value for m in ExternalSource} == {
        "printables",
        "thangs",
        "makerworld",
        "cults3d",
        "thingiverse",
        "other",
    }


def test_note_kind_enum_values():
    assert {m.value for m in NoteKind} == {
        "description",
        "operational",
        "ai_review",
        "other",
    }
