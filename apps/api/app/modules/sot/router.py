"""GET-only endpoints for the SoT entity tables.

Routes here read the new DB-backed entity tables. They coexist with
legacy /api/catalog/* (file-based) at distinct prefixes; legacy is left
untouched until the cutover slice.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.db.session import get_session
from app.modules.sot.schemas import CategoryTree, TagRead
from app.modules.sot.service import list_categories_tree, list_tags

router = APIRouter(prefix="/api", tags=["sot-read"])


@router.get("/categories", response_model=CategoryTree)
def get_categories(
    session: Annotated[Session, Depends(get_session)],
) -> CategoryTree:
    return list_categories_tree(session)


@router.get("/tags", response_model=list[TagRead])
def get_tags(
    session: Annotated[Session, Depends(get_session)],
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TagRead]:
    return list_tags(session, q=q, limit=limit)
