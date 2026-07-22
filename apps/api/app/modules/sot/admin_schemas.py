"""Request schemas for SoT admin write endpoints.

Kept separate from read-side schemas.py for symmetry — this module owns
everything the admin router accepts as input (body payloads).
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.db.models import ExternalSource, ModelFileKind, ModelSource, ModelStatus, NoteKind


class ModelCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name_en": "Stanford Bunny",
                    "name_pl": "Królik Stanforda",
                    "source": "printables",
                    "status": "not_printed",
                }
            ]
        }
    )

    name_en: str = Field(min_length=1)
    name_pl: str | None = None
    source: ModelSource = ModelSource.unknown
    status: ModelStatus = ModelStatus.not_printed
    rating: float | None = Field(default=None, ge=1.0, le=5.0)
    slug: str | None = None


class ModelPatch(BaseModel):
    """All fields optional.  Extra keys rejected to catch caller typos."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "status": "printed",
                    "rating": 4.5,
                }
            ]
        },
    )

    name_en: str | None = Field(default=None, min_length=1)
    name_pl: str | None = None
    source: ModelSource | None = None
    status: ModelStatus | None = None
    rating: float | None = Field(default=None, ge=1.0, le=5.0)
    slug: str | None = None


class ThumbnailSet(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"file_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
            ]
        }
    )

    file_id: uuid.UUID


class PhotoReorderRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ordered_ids": [
                        "11111111-1111-1111-1111-111111111111",
                        "22222222-2222-2222-2222-222222222222",
                    ]
                }
            ]
        }
    )

    ordered_ids: list[uuid.UUID]


class RenderRequest(BaseModel):
    """Optional STL selection for the render job. Empty = worker picks the first STL."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"selected_stl_file_ids": []},
                {"selected_stl_file_ids": ["33333333-3333-3333-3333-333333333333"]},
            ]
        }
    )

    selected_stl_file_ids: list[uuid.UUID] = Field(default_factory=list)


class ModelFilePatch(BaseModel):
    """Updateable fields for a ModelFile.  Content-tied fields (storage_path,
    sha256, size_bytes, mime_type) are intentionally excluded — replace the
    binary via DELETE + POST upload instead."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"original_name": "cali_cat_lid.stl"},
                {"selected_for_render": True},
            ]
        },
    )

    kind: ModelFileKind | None = None
    original_name: str | None = Field(default=None, min_length=1)
    selected_for_render: bool | None = None


# ---------------------------------------------------------------------------
# Tags M2M
# ---------------------------------------------------------------------------


class TagsReplace(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_ids": [
                        "44444444-4444-4444-4444-444444444444",
                        "55555555-5555-5555-5555-555555555555",
                    ]
                }
            ]
        }
    )

    tag_ids: list[uuid.UUID]


class TagAdd(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"tag_id": "44444444-4444-4444-4444-444444444444"},
            ]
        }
    )

    tag_id: uuid.UUID


# ---------------------------------------------------------------------------
# Tags global
# ---------------------------------------------------------------------------


class TagCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "slug": "miniatures",
                    "name_en": "Miniatures",
                    "name_pl": "Figurki",
                }
            ]
        }
    )

    slug: str = Field(min_length=1)
    name_en: str = Field(min_length=1)
    name_pl: str | None = None


class TagPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"name_pl": "Figurki kolekcjonerskie"},
                {"group_id": "88888888-8888-8888-8888-888888888888", "group_position": 0},
            ]
        },
    )

    slug: str | None = Field(default=None, min_length=1)
    name_en: str | None = Field(default=None, min_length=1)
    name_pl: str | None = None
    # Story 42.4 (D-MOVE-1) — move-to-group surface. `group_id` is the one
    # intentionally-nullable FK: explicit null makes the tag groupless. An
    # omitted field is untouched (not in exclude_unset).
    group_id: uuid.UUID | None = None
    group_position: int | None = None

    @field_validator("group_position")
    @classmethod
    def _reject_null_group_position(cls, v: int | None) -> int | None:
        # `Tag.group_position` is NOT NULL. Pydantic v2 skips validators for
        # omitted defaults, so this rejects ONLY an explicit `group_position:
        # null` → 422 (never a raw IntegrityError → 500; D-NULLSEM-1). `group_id`
        # gets no validator — null is meaningful (groupless).
        if v is None:
            raise ValueError("group_position may not be null")
        return v


class TagMerge(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "from_id": "66666666-6666-6666-6666-666666666666",
                    "to_id": "44444444-4444-4444-4444-444444444444",
                }
            ]
        }
    )

    from_id: uuid.UUID
    to_id: uuid.UUID


# ---------------------------------------------------------------------------
# Tag groups (Story 42.4 — admin governance)
# ---------------------------------------------------------------------------


class TagGroupCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "slug": "materials",
                    "name_en": "Materials",
                    "name_pl": "Materiały",
                    "position": 0,
                }
            ]
        }
    )

    slug: str = Field(min_length=1)
    name_en: str = Field(min_length=1)
    name_pl: str | None = None
    position: int = 0


class TagGroupPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"name_pl": "Materiały i wykończenie"},
                {"position": 2},
            ]
        },
    )

    slug: str | None = Field(default=None, min_length=1)
    name_en: str | None = Field(default=None, min_length=1)
    name_pl: str | None = None
    position: int | None = None

    @field_validator("slug", "name_en", "position")
    @classmethod
    def _reject_explicit_null(cls, v: object) -> object:
        # `TagGroup.slug/name_en/position` are NOT NULL. Pydantic v2 skips
        # validators for omitted defaults, so this rejects ONLY an explicit
        # `null` on these fields → 422 (never a NOT NULL violation surfacing as
        # the wrong 409/500; D-NULLSEM-1). `name_pl` gets no validator — null
        # clears it.
        if v is None:
            raise ValueError("field may not be null")
        return v


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


class NoteCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "kind": "description",
                    "body": "Single-wall vase mode; uses ~12 g of PLA at 0.28 mm layer height.",
                    "body_pl": "Tryb wazonu; ~12 g PLA przy warstwie 0.28 mm.",
                    "body_en": "Single-wall vase mode; uses ~12 g of PLA at 0.28 mm layer height.",
                }
            ]
        }
    )

    kind: NoteKind
    body: str = Field(min_length=1)
    # Initiative 10 Story 16.1 (Decision L) — bilingual fields for description-kind
    # notes. Optional on create; admin UI may populate either, both, or neither
    # (legacy body-only writes continue to work for backward compatibility).
    body_pl: str | None = Field(default=None, min_length=1)
    body_en: str | None = Field(default=None, min_length=1)


class NotePatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"body": "Re-tested 2026-05; PETG works too at 245 °C."},
                {"body_pl": "Przetestowane 2026-05; PETG też działa przy 245 °C."},
            ]
        },
    )

    kind: NoteKind | None = None
    body: str | None = Field(default=None, min_length=1)
    body_pl: str | None = Field(default=None, min_length=1)
    body_en: str | None = Field(default=None, min_length=1)


# ---------------------------------------------------------------------------
# Prints
# ---------------------------------------------------------------------------


class PrintCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "printed_at": "2026-05-08",
                    "note": "K1 Max, 0.4 nozzle, PLA, 220 °C / 60 °C, 25% infill",
                    "photo_file_id": None,
                }
            ]
        }
    )

    printed_at: datetime.date | None = None
    note: str | None = None
    photo_file_id: uuid.UUID | None = None


class PrintPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"note": "Layer adhesion issue near top — bumped temp 5 °C and reprinted."},
            ]
        },
    )

    printed_at: datetime.date | None = None
    note: str | None = None
    photo_file_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# External links
# ---------------------------------------------------------------------------


class ExternalLinkCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source": "printables",
                    "external_id": "661995",
                    "url": "https://www.printables.com/model/661995-stanford-bunny",
                }
            ]
        }
    )

    source: ExternalSource
    external_id: str | None = None
    url: str = Field(min_length=1)


class ExternalLinkPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"url": "https://www.printables.com/model/661995"},
            ]
        },
    )

    source: ExternalSource | None = None
    external_id: str | None = None
    url: str | None = Field(default=None, min_length=1)
