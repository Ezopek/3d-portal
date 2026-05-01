from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    decorations = "decorations"
    printer_3d = "printer_3d"
    gridfinity = "gridfinity"
    multiboard = "multiboard"
    tools = "tools"
    practical = "practical"
    premium = "premium"
    own_models = "own_models"
    other = "other"


class Status(StrEnum):
    not_printed = "not_printed"
    in_progress = "in_progress"
    printed = "printed"
    needs_revision = "needs_revision"


class Source(StrEnum):
    printables = "printables"
    thangs = "thangs"
    thingiverse = "thingiverse"
    makerworld = "makerworld"
    creality_cloud = "creality_cloud"
    own = "own"
    premium = "premium"
    unknown = "unknown"


class Print(BaseModel):
    path: str
    date: str
    notes_en: str = ""
    notes_pl: str = ""


class Model(BaseModel):
    id: str
    name_en: str
    name_pl: str
    path: str
    category: Category
    subcategory: str = ""
    tags: list[str] = Field(default_factory=list)
    source: Source = Source.unknown
    printables_id: str | None = None
    thangs_id: str | None = None
    makerworld_id: str | None = None
    source_url: str | None = None
    rating: int | None = None
    status: Status = Status.not_printed
    notes: str = ""
    thumbnail: str | None = None
    thumbnail_url: str | None = None
    date_added: str
    prints: list[Print] = Field(default_factory=list)


class ModelListItem(BaseModel):
    id: str
    name_en: str
    name_pl: str
    category: Category
    tags: list[str]
    source: Source
    status: Status
    rating: int | None
    thumbnail_url: str | None  # API-relative URL
    has_3d: bool
    date_added: str
    image_count: int = 0


class ModelListResponse(BaseModel):
    models: list[ModelListItem]
    total: int
