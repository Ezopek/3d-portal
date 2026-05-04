from fastapi import APIRouter

from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.catalog.files import router as files_router
from app.modules.catalog.router import router as catalog_router
from app.modules.share.admin_router import router as share_admin_router
from app.modules.share.router import router as share_router
from app.modules.sot.router import router as sot_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(catalog_router)
api_router.include_router(files_router)
api_router.include_router(admin_router)
api_router.include_router(share_admin_router)
api_router.include_router(share_router)
api_router.include_router(sot_router)
