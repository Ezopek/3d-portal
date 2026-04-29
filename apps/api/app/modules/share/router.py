from fastapi import APIRouter, HTTPException, Request

from app.modules.share.models import ShareModelView
from app.modules.share.service import ShareService

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/{token}", response_model=ShareModelView)
async def resolve_share(token: str, request: Request) -> ShareModelView:
    service = ShareService(redis=request.app.state.redis.get())
    record = await service.resolve(token)
    if record is None:
        raise HTTPException(404, "Share token not found or expired")

    catalog = request.app.state.catalog_service
    model = catalog.get_model(record.model_id)
    if model is None:
        raise HTTPException(404, "Model no longer exists")

    images = []
    images_dir = catalog._catalog_dir / model.path / "images"  # noqa: SLF001
    if images_dir.is_dir():
        for child in sorted(images_dir.iterdir()):
            if child.is_file() and child.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                images.append(f"/api/files/{model.id}/images/{child.name}")

    has_3d = catalog._has_3d(model)  # noqa: SLF001
    thumbnail = catalog._resolve_thumbnail(model)  # noqa: SLF001

    # Find first STL for the share view's download button
    catalog_root = catalog._catalog_dir / model.path  # noqa: SLF001
    stl_url = None
    if catalog_root.is_dir():
        for stl in sorted(catalog_root.rglob("*.stl")):
            rel = stl.relative_to(catalog_root).as_posix()
            stl_url = f"/api/files/{model.id}/{rel}"
            break

    return ShareModelView(
        id=model.id,
        name_en=model.name_en,
        name_pl=model.name_pl,
        category=model.category.value,
        tags=model.tags,
        thumbnail_url=thumbnail,
        has_3d=has_3d,
        images=images,
        notes_en=model.notes,
        notes_pl="",  # spec keeps notes English-only on the model; PL field reserved for future
        stl_url=stl_url,
    )
