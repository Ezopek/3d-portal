"""Initiative 5 / Epic 7 — TOTP 2FA enrollment surface (Story 7.2).

Re-exports the public router + service + schemas so callers import from the
package root, matching the ``apps/api/app/modules/invite/`` precedent.
"""

from app.modules.auth.totp.router import router as enroll_router
from app.modules.auth.totp.schemas import (
    ConfirmRequest,
    ConfirmResponse,
    EnrollResponse,
    StatusResponse,
)
from app.modules.auth.totp.service import Settings2faService

Enrollment2faPayload = ConfirmRequest

__all__ = [
    "ConfirmRequest",
    "ConfirmResponse",
    "EnrollResponse",
    "Enrollment2faPayload",
    "Settings2faService",
    "StatusResponse",
    "enroll_router",
]
