"""Admin write endpoints for Model CRUD and secondary resources.

Prefix: /api/admin
Auth: all endpoints require admin OR agent JWT.
Hard-delete (?hard=true) is restricted to admin role only.
"""

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.auth.jwt import TokenError, decode_token
from app.core.config import Settings, get_settings
from app.core.db.models import ModelFileKind, User, UserRole
from app.core.db.session import get_session
from app.modules.sot.admin_schemas import (
    CategoryCreate,
    CategoryPatch,
    ExternalLinkCreate,
    ExternalLinkPatch,
    ModelCreate,
    ModelFilePatch,
    ModelPatch,
    NoteCreate,
    NotePatch,
    PrintCreate,
    PrintPatch,
    TagAdd,
    TagCreate,
    TagMerge,
    TagPatch,
    TagsReplace,
    ThumbnailSet,
)
from app.modules.sot.admin_service import (
    add_model_tag,
    create_category,
    create_external_link,
    create_model,
    create_note,
    create_print,
    create_tag,
    delete_category,
    delete_external_link,
    delete_model_file,
    delete_note,
    delete_print,
    delete_tag,
    hard_delete_model,
    merge_tags,
    remove_model_tag,
    replace_model_tags,
    restore_model,
    set_thumbnail,
    soft_delete_model,
    update_category,
    update_external_link,
    update_model,
    update_model_file,
    update_note,
    update_print,
    update_tag,
    upload_model_file,
)
from app.modules.sot.schemas import (
    CategorySummary,
    ExternalLinkRead,
    ModelDetail,
    ModelFileRead,
    NoteRead,
    PrintRead,
    TagRead,
)
from app.modules.sot.service import get_model_detail

router = APIRouter(prefix="/api/admin", tags=["sot-admin"])

# ---------------------------------------------------------------------------
# Auth dependency — allows both admin and agent roles
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def _current_admin_or_agent_dep(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> uuid.UUID:
    if creds is None:
        raise HTTPException(401, "Missing bearer token")
    try:
        claims = decode_token(creds.credentials, secret=settings.jwt_secret)
    except TokenError as exc:
        raise HTTPException(401, "Invalid token") from exc
    role = claims.get("role")
    if role not in ("admin", "agent"):
        raise HTTPException(403, "Admin or agent role required")
    try:
        return uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(401, "Malformed subject claim") from exc


_current_principal = Depends(_current_admin_or_agent_dep)


def _require_admin_role(session: Session, user_id: uuid.UUID) -> None:
    """Raise 403 if *user_id* does not have the admin role."""
    user = session.get(User, user_id)
    if user is None or user.role != UserRole.admin:
        raise HTTPException(403, "hard delete requires admin role")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/models", status_code=201, response_model=ModelDetail)
def admin_create_model(
    payload: ModelCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> ModelDetail:
    try:
        m = create_model(session, payload=payload, actor_user_id=actor_user_id)
    except ValueError as exc:
        msg = str(exc)
        if "category not found" in msg:
            raise HTTPException(400, "category not found") from exc
        if "slug_conflict" in msg:
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, msg) from exc

    detail = get_model_detail(session, m.id, include_deleted=True)
    if detail is None:  # shouldn't happen right after creation
        raise HTTPException(500, "model disappeared after create")
    return detail


@router.patch("/models/{model_id}", response_model=ModelDetail)
def admin_patch_model(
    model_id: uuid.UUID,
    patch: ModelPatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> ModelDetail:
    from sqlmodel import select

    from app.core.db.models import Model

    m = session.exec(select(Model).where(Model.id == model_id, Model.deleted_at.is_(None))).first()
    if m is None:
        raise HTTPException(404, "model not found")

    try:
        m = update_model(session, model=m, patch=patch, actor_user_id=actor_user_id)
    except ValueError as exc:
        msg = str(exc)
        if "category not found" in msg:
            raise HTTPException(400, "category not found") from exc
        if "slug_conflict" in msg:
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, msg) from exc

    detail = get_model_detail(session, m.id, include_deleted=True)
    if detail is None:
        raise HTTPException(500, "model disappeared after update")
    return detail


@router.post("/models/{model_id}/restore", response_model=ModelDetail)
def admin_restore_model(
    model_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> ModelDetail:
    try:
        m = restore_model(session, model_id=model_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, "model not found") from exc

    detail = get_model_detail(session, m.id, include_deleted=True)
    if detail is None:
        raise HTTPException(500, "model disappeared after restore")
    return detail


@router.delete("/models/{model_id}", status_code=200, response_model=ModelDetail)
def admin_delete_model(
    model_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    hard: bool = Query(default=False),
    actor_user_id: uuid.UUID = _current_principal,
) -> ModelDetail | Response:
    if hard:
        _require_admin_role(session, actor_user_id)
        settings = get_settings()
        try:
            hard_delete_model(
                session,
                model_id=model_id,
                actor_user_id=actor_user_id,
                content_dir=settings.portal_content_dir,
            )
        except LookupError as exc:
            raise HTTPException(404, "model not found") from exc
        return Response(status_code=200)

    # Soft delete
    try:
        m = soft_delete_model(session, model_id=model_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, "model not found") from exc

    detail = get_model_detail(session, m.id, include_deleted=True)
    if detail is None:
        raise HTTPException(500, "model disappeared after soft delete")
    return detail


@router.put("/models/{model_id:uuid}/thumbnail", response_model=ModelDetail)
def admin_set_thumbnail(
    model_id: uuid.UUID,
    payload: ThumbnailSet,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> ModelDetail:
    try:
        m = set_thumbnail(
            session,
            model_id=model_id,
            file_id=payload.file_id,
            actor_user_id=actor_user_id,
        )
    except LookupError as exc:
        raise HTTPException(404, "model not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    detail = get_model_detail(session, m.id, include_deleted=True)
    if detail is None:
        raise HTTPException(500, "model disappeared after thumbnail update")
    return detail


# ---------------------------------------------------------------------------
# ModelFile endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/models/{model_id}/files",
    response_model=ModelFileRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Existing file returned (sha256 dedup)"},
        201: {"description": "File uploaded"},
        413: {"description": "File too large"},
    },
)
async def admin_upload_file(
    model_id: uuid.UUID,
    response: Response,
    file: Annotated[UploadFile, File()],
    kind: Annotated[ModelFileKind, Form()],
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> ModelFileRead:
    settings = get_settings()
    file_row, was_existing = await upload_model_file(
        session,
        model_id=model_id,
        kind=kind,
        upload=file,
        actor_user_id=actor_user_id,
        content_dir=settings.portal_content_dir,
    )
    if was_existing:
        response.status_code = status.HTTP_200_OK
    return ModelFileRead.model_validate(file_row)


@router.patch(
    "/models/{model_id}/files/{file_id}",
    response_model=ModelFileRead,
)
def admin_patch_file(
    model_id: uuid.UUID,
    file_id: uuid.UUID,
    patch: ModelFilePatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> ModelFileRead:
    try:
        f = update_model_file(
            session,
            model_id=model_id,
            file_id=file_id,
            patch=patch,
            actor_user_id=actor_user_id,
        )
    except LookupError as exc:
        raise HTTPException(404, "file not found") from exc
    except ValueError as exc:
        msg = str(exc)
        if "kind_conflict" in msg:
            raise HTTPException(
                409, "kind change would violate unique (model, sha256, kind)"
            ) from exc
        raise HTTPException(422, msg) from exc
    return ModelFileRead.model_validate(f)


@router.delete(
    "/models/{model_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def admin_delete_file(
    model_id: uuid.UUID,
    file_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> None:
    settings = get_settings()
    try:
        delete_model_file(
            session,
            model_id=model_id,
            file_id=file_id,
            actor_user_id=actor_user_id,
            content_dir=settings.portal_content_dir,
        )
    except LookupError as exc:
        raise HTTPException(404, "file not found") from exc


# ---------------------------------------------------------------------------
# Tags M2M
# ---------------------------------------------------------------------------


@router.put("/models/{model_id}/tags", response_model=list[TagRead])
def admin_replace_model_tags(
    model_id: uuid.UUID,
    payload: TagsReplace,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> list[TagRead]:
    try:
        tags = replace_model_tags(
            session, model_id=model_id, payload=payload, actor_user_id=actor_user_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return [TagRead.model_validate(t) for t in tags]


@router.post("/models/{model_id}/tags", response_model=list[TagRead])
def admin_add_model_tag(
    model_id: uuid.UUID,
    payload: TagAdd,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> list[TagRead]:
    try:
        tags = add_model_tag(
            session, model_id=model_id, tag_id=payload.tag_id, actor_user_id=actor_user_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return [TagRead.model_validate(t) for t in tags]


@router.delete("/models/{model_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_remove_model_tag(
    model_id: uuid.UUID,
    tag_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> None:
    try:
        remove_model_tag(session, model_id=model_id, tag_id=tag_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


# ---------------------------------------------------------------------------
# Tags global
# ---------------------------------------------------------------------------


@router.post("/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def admin_create_tag(
    payload: TagCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> TagRead:
    try:
        tag = create_tag(session, payload=payload, actor_user_id=actor_user_id)
    except ValueError as exc:
        if "slug_conflict" in str(exc):
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, str(exc)) from exc
    return TagRead.model_validate(tag)


@router.post("/tags/merge", response_model=TagRead)
def admin_merge_tags(
    payload: TagMerge,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> TagRead:
    try:
        tag = merge_tags(session, payload=payload, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return TagRead.model_validate(tag)


@router.patch("/tags/{tag_id}", response_model=TagRead)
def admin_patch_tag(
    tag_id: uuid.UUID,
    patch: TagPatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> TagRead:
    try:
        tag = update_tag(session, tag_id=tag_id, patch=patch, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        if "slug_conflict" in str(exc):
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, str(exc)) from exc
    return TagRead.model_validate(tag)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_tag(
    tag_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> None:
    try:
        delete_tag(session, tag_id=tag_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        if "tag_in_use" in str(exc):
            raise HTTPException(409, "tag is in use by one or more models") from exc
        raise HTTPException(422, str(exc)) from exc


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@router.post("/categories", response_model=CategorySummary, status_code=status.HTTP_201_CREATED)
def admin_create_category(
    payload: CategoryCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> CategorySummary:
    try:
        cat = create_category(session, payload=payload, actor_user_id=actor_user_id)
    except ValueError as exc:
        msg = str(exc)
        if "parent not found" in msg:
            raise HTTPException(400, "parent category not found") from exc
        if "slug_conflict" in msg:
            raise HTTPException(409, "slug already exists for this parent") from exc
        raise HTTPException(422, msg) from exc
    return CategorySummary.model_validate(cat)


@router.patch("/categories/{category_id}", response_model=CategorySummary)
def admin_patch_category(
    category_id: uuid.UUID,
    patch: CategoryPatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> CategorySummary:
    try:
        cat = update_category(
            session, category_id=category_id, patch=patch, actor_user_id=actor_user_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        msg = str(exc)
        if "parent not found" in msg:
            raise HTTPException(400, "parent category not found") from exc
        if "cycle" in msg:
            raise HTTPException(400, "would create a cycle") from exc
        if "slug_conflict" in msg:
            raise HTTPException(409, "slug already exists for this parent") from exc
        raise HTTPException(422, msg) from exc
    return CategorySummary.model_validate(cat)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_category(
    category_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> None:
    try:
        delete_category(session, category_id=category_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        if "category_in_use" in str(exc):
            raise HTTPException(409, "category has models or child categories") from exc
        raise HTTPException(422, str(exc)) from exc


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@router.post(
    "/models/{model_id}/notes",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_note(
    model_id: uuid.UUID,
    payload: NoteCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> NoteRead:
    try:
        note = create_note(session, model_id=model_id, payload=payload, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return NoteRead.model_validate(note)


@router.patch("/notes/{note_id}", response_model=NoteRead)
def admin_patch_note(
    note_id: uuid.UUID,
    patch: NotePatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> NoteRead:
    try:
        note = update_note(session, note_id=note_id, patch=patch, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return NoteRead.model_validate(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_note(
    note_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> None:
    try:
        delete_note(session, note_id=note_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


# ---------------------------------------------------------------------------
# Prints
# ---------------------------------------------------------------------------


@router.post(
    "/models/{model_id}/prints",
    response_model=PrintRead,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_print(
    model_id: uuid.UUID,
    payload: PrintCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> PrintRead:
    try:
        pr = create_print(session, model_id=model_id, payload=payload, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return PrintRead.model_validate(pr)


@router.patch("/prints/{print_id}", response_model=PrintRead)
def admin_patch_print(
    print_id: uuid.UUID,
    patch: PrintPatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> PrintRead:
    try:
        pr = update_print(session, print_id=print_id, patch=patch, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return PrintRead.model_validate(pr)


@router.delete("/prints/{print_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_print(
    print_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> None:
    try:
        delete_print(session, print_id=print_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


# ---------------------------------------------------------------------------
# External links
# ---------------------------------------------------------------------------


@router.post(
    "/models/{model_id}/external-links",
    response_model=ExternalLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_external_link(
    model_id: uuid.UUID,
    payload: ExternalLinkCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> ExternalLinkRead:
    try:
        link = create_external_link(
            session, model_id=model_id, payload=payload, actor_user_id=actor_user_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        if "source_conflict" in str(exc):
            raise HTTPException(409, "model already has a link for this source") from exc
        raise HTTPException(422, str(exc)) from exc
    return ExternalLinkRead.model_validate(link)


@router.patch("/external-links/{link_id}", response_model=ExternalLinkRead)
def admin_patch_external_link(
    link_id: uuid.UUID,
    patch: ExternalLinkPatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> ExternalLinkRead:
    try:
        link = update_external_link(
            session, link_id=link_id, patch=patch, actor_user_id=actor_user_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        if "source_conflict" in str(exc):
            raise HTTPException(409, "model already has a link for this source") from exc
        raise HTTPException(422, str(exc)) from exc
    return ExternalLinkRead.model_validate(link)


@router.delete("/external-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_external_link(
    link_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = _current_principal,
) -> None:
    try:
        delete_external_link(session, link_id=link_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
