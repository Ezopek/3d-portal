from fastapi import APIRouter

from app.modules.admin.router import router as admin_router
from app.modules.auth.password_reset.admin_router import router as password_reset_admin_router
from app.modules.auth.password_reset.router import router as password_reset_public_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.totp.router import router as totp_router
from app.modules.invite.admin_router import router as invite_admin_router
from app.modules.invite.router import router as invite_public_router
from app.modules.share.admin_router import router as share_admin_router
from app.modules.share.member_router import router as share_member_router
from app.modules.share.router import router as share_router
from app.modules.slicer.router import router as estimates_router
from app.modules.sot.admin_router import router as sot_admin_router
from app.modules.sot.router import router as sot_router
from app.modules.spools.router import router as spools_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(totp_router)
api_router.include_router(invite_public_router)
api_router.include_router(invite_admin_router)
api_router.include_router(password_reset_public_router)
api_router.include_router(password_reset_admin_router)
api_router.include_router(sot_admin_router)
api_router.include_router(admin_router)
api_router.include_router(share_admin_router)
api_router.include_router(share_member_router)
api_router.include_router(share_router)
api_router.include_router(sot_router)
api_router.include_router(spools_router)
api_router.include_router(estimates_router)
