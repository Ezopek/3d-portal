from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import nullslast
from sqlmodel import Session, select

from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
    ModelTag,
    Tag,
)
from app.core.db.session import get_session
from app.modules.share.models import ShareModelView
from app.modules.share.service import ShareService

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/{token}", response_model=ShareModelView)
async def resolve_share(
    token: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> ShareModelView:
    service = ShareService(redis=request.app.state.redis.get())
    record = await service.resolve(token)
    if record is None:
        raise HTTPException(404, "Share token not found or expired")

    model = session.exec(
        select(Model).where(Model.id == record.model_id, Model.deleted_at.is_(None))
    ).first()
    if model is None:
        raise HTTPException(404, "Model no longer exists")

    category = session.exec(select(Category).where(Category.id == model.category_id)).one()

    tag_rows = session.exec(
        select(Tag.name_en)
        .join(ModelTag, ModelTag.tag_id == Tag.id)
        .where(ModelTag.model_id == model.id)
        .order_by(Tag.slug)
    ).all()
    tags = list(tag_rows)

    image_files = session.exec(
        select(ModelFile.id)
        .where(ModelFile.model_id == model.id)
        .where(ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print]))
        .order_by(nullslast(ModelFile.position.asc()), ModelFile.created_at.asc())
    ).all()
    images = [f"/api/models/{model.id}/files/{fid}/content" for fid in image_files]

    thumbnail_url = None
    if model.thumbnail_file_id is not None:
        thumbnail_url = (
            f"/api/models/{model.id}/files/{model.thumbnail_file_id}/content"
        )
    elif images:
        thumbnail_url = images[0]

    stl_row = session.exec(
        select(ModelFile.id)
        .where(ModelFile.model_id == model.id)
        .where(ModelFile.kind == ModelFileKind.stl)
        .order_by(ModelFile.created_at.asc())
    ).first()
    stl_url = (
        f"/api/models/{model.id}/files/{stl_row}/content?download=1"
        if stl_row is not None
        else None
    )

    return ShareModelView(
        id=model.id,
        name_en=model.name_en,
        name_pl=model.name_pl,
        category=category.slug,
        tags=tags,
        thumbnail_url=thumbnail_url,
        has_3d=stl_row is not None,
        images=images,
        notes_en="",
        notes_pl="",
        stl_url=stl_url,
    )
