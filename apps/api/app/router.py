from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.catalog.files import router as files_router
from app.modules.catalog.router import router as catalog_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(catalog_router)
api_router.include_router(files_router)
