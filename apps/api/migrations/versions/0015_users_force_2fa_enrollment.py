"""force_2fa_enrollment column on user for Initiative 5 / Epic 8 / Story 8.4.

Revision ID: 0015_users_force_2fa_enrollment
Revises: 0014_users_is_active_last_active
Create Date: 2026-05-20

Story 8.4 (admin 2FA overrides) materializes Decision F §1553 per-user
override path for the force-enroll direction: a one-bit flag the admin
sets via ``POST /api/admin/users/{id}/force-2fa-enrollment`` that the
``POST /api/auth/login`` handler ORs into its ``totp_enroll_required``
expression. Without this column on disk, the admin endpoint has nowhere
to write and the login handler has nothing to read — the entire per-user
override path is dead code.

``user.force_2fa_enrollment`` is ``BOOLEAN NOT NULL DEFAULT FALSE``
(Decision F per-user override path; epics §1798 verbatim "implementation:
set a ``users.force_2fa_enrollment BOOLEAN`` flag"). The existing
``admin`` + ``agent`` rows seeded by ``seed_admin()`` plus all ``member``
rows backfill to FALSE atomically via the server-side default, so the
migration is null-op for live data (NFR5-INT-1). The flag is "one-shot"
per epics §1798: once True, the next successful TOTP enrollment-confirm
auto-clears the flag (see ``confirm_enrollment`` handler at
``apps/api/app/modules/auth/totp/router.py:139-188``).

No new table; no new index. The column is a bool-typed admin-tier filter
(visible in the AdminUserListItem projection per AC-6) and explicitly NOT
on the sortable allowlist (Story 8.2 ``sort_by`` ``Literal`` constraint
stays unchanged). The column is part of the existing ``user`` table.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_users_force_2fa_enrollment"
down_revision = "0014_users_is_active_last_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "force_2fa_enrollment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "force_2fa_enrollment")
