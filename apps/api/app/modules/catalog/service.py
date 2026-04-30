import json
import logging
import threading
from pathlib import Path

from app.modules.catalog.models import Model, ModelListItem, ModelListResponse
from app.modules.catalog.thumbnail_overrides import ThumbnailOverrideRepo

_log = logging.getLogger(__name__)
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


class CatalogService:
    def __init__(
        self,
        *,
        catalog_dir: Path,
        renders_dir: Path,
        index_path: Path,
        overrides: ThumbnailOverrideRepo,
    ) -> None:
        self._catalog_dir = catalog_dir
        self._renders_dir = renders_dir
        self._index_path = index_path
        self._overrides = overrides
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
                _log.warning("catalog index missing at %s — serving empty", self._index_path)
                return {}
            models = [Model.model_validate(entry) for entry in raw]
            self._cache = {m.id: m for m in models}
            return self._cache

    # --- public API --------------------------------------------------------

    def list_models(self) -> ModelListResponse:
        models = self._load()
        overrides = self._overrides.get_all()
        items = [self._project(m, overrides) for m in models.values()]
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

    def thumbnail_target_exists(self, model_id: str, relative_path: str) -> bool:
        model = self.get_model(model_id)
        if model is None:
            return False
        return self._target_path(model, relative_path) is not None

    # --- helpers -----------------------------------------------------------

    def _project(self, m: Model, overrides: dict[str, str]) -> ModelListItem:
        thumbnail_url = self._resolve_thumbnail(m, overrides.get(m.id))
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

    def _resolve_thumbnail(self, m: Model, override: str | None) -> str | None:
        # 1. Override (silent fallback if file disappeared).
        if override is not None and self._target_path(m, override) is not None:
            return f"/api/files/{m.id}/{override}"

        # 2. images/* in catalog.
        images_dir = self._catalog_dir / m.path / "images"
        if images_dir.is_dir():
            for child in sorted(images_dir.iterdir()):
                if child.is_file() and child.suffix.lower() in _IMAGE_EXTS:
                    return f"/api/files/{m.id}/images/{child.name}"

        # 3. Newest entry from Model.prints[].date that resolves to an existing image file.
        for p in sorted(m.prints, key=lambda x: x.date, reverse=True):
            rel = self._strip_model_prefix(m, p.path)
            if rel.lower().endswith(_IMAGE_EXTS) and (self._catalog_dir / m.path / rel).is_file():
                return f"/api/files/{m.id}/{rel}"

        # 4. Computed iso render.
        if (self._renders_dir / m.id / "iso.png").is_file():
            return f"/api/files/{m.id}/iso.png"

        return None

    def _strip_model_prefix(self, m: Model, full_path: str) -> str:
        prefix = m.path + "/"
        if full_path.startswith(prefix):
            return full_path[len(prefix) :]
        return full_path

    def _target_path(self, m: Model, relative_path: str) -> Path | None:
        catalog_candidate = self._catalog_dir / m.path / relative_path
        if catalog_candidate.is_file():
            return catalog_candidate
        renders_candidate = self._renders_dir / m.id / relative_path
        if renders_candidate.is_file():
            return renders_candidate
        return None

    def _has_3d(self, m: Model) -> bool:
        root = self._catalog_dir / m.path
        if not root.is_dir():
            return False
        return any(any(root.rglob(f"*{ext}")) for ext in (".stl", ".3mf", ".step"))
