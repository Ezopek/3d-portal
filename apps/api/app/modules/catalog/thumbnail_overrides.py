import uuid
from collections.abc import Callable

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db.models import ThumbnailOverride


class ThumbnailOverrideRepo:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, model_id: str) -> str | None:
        with Session(self._engine) as s:
            row = s.get(ThumbnailOverride, model_id)
            return row.relative_path if row is not None else None

    def get_all(self) -> dict[str, str]:
        with Session(self._engine) as s:
            rows = s.exec(select(ThumbnailOverride)).all()
            return {r.model_id: r.relative_path for r in rows}

    def set(self, *, model_id: str, relative_path: str, user_id: uuid.UUID) -> None:
        with Session(self._engine) as s:
            row = s.get(ThumbnailOverride, model_id)
            if row is None:
                row = ThumbnailOverride(
                    model_id=model_id,
                    relative_path=relative_path,
                    set_by_user_id=user_id,
                )
            else:
                row.relative_path = relative_path
                row.set_by_user_id = user_id
            s.add(row)
            s.commit()

    def clear(self, model_id: str) -> bool:
        with Session(self._engine) as s:
            row = s.get(ThumbnailOverride, model_id)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True

    def purge_orphans(
        self,
        *,
        exists: Callable[[str, str], bool],
    ) -> list[tuple[str, str]]:
        with Session(self._engine) as s:
            rows = s.exec(select(ThumbnailOverride)).all()
            removed: list[tuple[str, str]] = []
            for row in rows:
                if not exists(row.model_id, row.relative_path):
                    removed.append((row.model_id, row.relative_path))
                    s.delete(row)
            if removed:
                s.commit()
            return removed
