import json
from collections.abc import Callable

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db.models import RenderSelection


class RenderSelectionRepo:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, model_id: str) -> list[str]:
        with Session(self._engine) as s:
            row = s.get(RenderSelection, model_id)
            if row is None:
                return []
            return json.loads(row.selected_paths)

    def get_all(self) -> dict[str, list[str]]:
        with Session(self._engine) as s:
            rows = s.exec(select(RenderSelection)).all()
            return {r.model_id: json.loads(r.selected_paths) for r in rows}

    def set(self, *, model_id: str, paths: list[str], user_id: int) -> None:
        encoded = json.dumps(list(paths))
        with Session(self._engine) as s:
            row = s.get(RenderSelection, model_id)
            if row is None:
                row = RenderSelection(
                    model_id=model_id,
                    selected_paths=encoded,
                    set_by_user_id=user_id,
                )
            else:
                row.selected_paths = encoded
                row.set_by_user_id = user_id
            s.add(row)
            s.commit()

    def clear(self, model_id: str) -> bool:
        with Session(self._engine) as s:
            row = s.get(RenderSelection, model_id)
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
        purged: list[tuple[str, str]] = []
        with Session(self._engine) as s:
            rows = s.exec(select(RenderSelection)).all()
            for row in rows:
                paths = json.loads(row.selected_paths)
                kept = [p for p in paths if exists(row.model_id, p)]
                if len(kept) == len(paths):
                    continue
                for p in paths:
                    if p not in kept:
                        purged.append((row.model_id, p))
                if not kept:
                    s.delete(row)
                else:
                    row.selected_paths = json.dumps(kept)
                    s.add(row)
            if purged:
                s.commit()
        return purged
