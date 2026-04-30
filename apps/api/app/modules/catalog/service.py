import json
import logging
import threading
from pathlib import Path

from app.modules.catalog.models import Model, ModelListItem, ModelListResponse

_log = logging.getLogger(__name__)


class CatalogService:
    def __init__(self, *, catalog_dir: Path, renders_dir: Path, index_path: Path) -> None:
        self._catalog_dir = catalog_dir
        self._renders_dir = renders_dir
        self._index_path = index_path
        self._lock = threading.RLock()
        self._cache: dict[str, Model] | None = None

    def refresh(self) -> None:
        with self._lock:
            self._cache = None

    def _load(self) -> dict[str, Model]:
        with self._lock:
            if self._cache is not None:
                return self._cache
            try:
                raw = json.loads(self._index_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                # Transient during catalog sync: behave as empty rather than 500.
                # Do NOT cache — next call retries so the catalog recovers as soon
                # as the index reappears (a manual refresh is not required).
                _log.warning("catalog index missing at %s — serving empty", self._index_path)
                return {}
            models = [Model.model_validate(entry) for entry in raw]
            self._cache = {m.id: m for m in models}
            return self._cache

    # --- public API --------------------------------------------------------

    def list_models(self) -> ModelListResponse:
        models = self._load()
        items = [self._project(m) for m in models.values()]
        items.sort(key=lambda m: m.date_added, reverse=True)
        return ModelListResponse(models=items, total=len(items))

    def get_model(self, model_id: str) -> Model | None:
        return self._load().get(model_id)

    def list_files(self, model_id: str) -> list[str]:
        model = self.get_model(model_id)
        if model is None:
            return []
        root = self._catalog_dir / model.path
        if not root.is_dir():
            return []
        return sorted(
            str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()
        )

    # --- helpers -----------------------------------------------------------

    def _project(self, m: Model) -> ModelListItem:
        thumbnail_url = self._resolve_thumbnail(m)
        has_3d = self._has_3d(m)
        return ModelListItem(
            id=m.id,
            name_en=m.name_en,
            name_pl=m.name_pl,
            category=m.category,
            tags=m.tags,
            source=m.source,
            status=m.status,
            rating=m.rating,
            thumbnail_url=thumbnail_url,
            has_3d=has_3d,
            date_added=m.date_added,
        )

    def _resolve_thumbnail(self, m: Model) -> str | None:
        images_dir = self._catalog_dir / m.path / "images"
        if images_dir.is_dir():
            for child in sorted(images_dir.iterdir()):
                if child.is_file() and child.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    return f"/api/files/{m.id}/images/{child.name}"
        # Fall back to a worker-computed render so list cards aren't blank
        # when the source catalog has no images/ folder.
        if (self._renders_dir / m.id / "front.png").is_file():
            return f"/api/files/{m.id}/front.png"
        return None

    def _has_3d(self, m: Model) -> bool:
        root = self._catalog_dir / m.path
        if not root.is_dir():
            return False
        return any(any(root.rglob(f"*{ext}")) for ext in (".stl", ".3mf", ".step"))
