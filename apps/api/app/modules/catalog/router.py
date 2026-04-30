from fastapi import APIRouter, HTTPException, Request

from app.modules.catalog.models import Model, ModelListResponse

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


def _service(request: Request):
    return request.app.state.catalog_service


@router.get("/models", response_model=ModelListResponse)
def list_models(request: Request) -> ModelListResponse:
    return _service(request).list_models()


@router.get("/models/{model_id}", response_model=Model)
def get_model(model_id: str, request: Request) -> Model:
    service = _service(request)
    model = service.get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")
    overrides = request.app.state.thumbnail_overrides.get_all()
    return model.model_copy(
        update={
            "thumbnail_url": service._resolve_thumbnail(model, overrides.get(model_id)),
        }
    )


@router.get("/models/{model_id}/files")
def list_files(model_id: str, request: Request) -> dict[str, list[str]]:
    service = _service(request)
    if service.get_model(model_id) is None:
        raise HTTPException(404, f"Model {model_id} not found")
    return {"files": service.list_files(model_id)}
