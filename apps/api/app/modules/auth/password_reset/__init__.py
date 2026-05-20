"""Initiative 5 admin-issued password-reset feature module (Story 8.5).

Realizes the Story 8.4 §file-structure-requirements deferred sub-router
promotion ("Story 8.5's password-reset endpoints will push the file over
500 LOC + introduce a distinct Redis-token concern — THAT is the natural
sub-router promotion point"). Follows the ``auth/totp/`` precedent (NOT
the ``invite/`` precedent) because there is NO ``password_resets`` DB
table — Redis is the SOLE state surface per epics §1814.
"""

from app.modules.auth.password_reset.schemas import (
    PasswordResetConsumeRequest,
    PasswordResetMintResponse,
)
from app.modules.auth.password_reset.service import PasswordResetService

__all__ = [
    "PasswordResetConsumeRequest",
    "PasswordResetMintResponse",
    "PasswordResetService",
]
