"""is_active + last_active_at columns on users for Initiative 5 / Epic 8.

Revision ID: 0014_users_is_active_last_active
Revises: 0013_users_2fa_columns
Create Date: 2026-05-20

Initiative 5 (E8) admin-panel + activity-throttle primitives. Architecture
Decision I (architecture.md §1601-1630) materializes both columns in one
migration because (a) Stories 8.2 + 8.3 (admin Users tab + per-user actions)
cannot ship without ``is_active`` existing on disk AND ``last_active_at``
being populated by something, and (b) shipping them as two separate
migrations would split the on-disk schema state across two PRs for no
operator value — the columns travel together logically (one says "can this
user log in?", the other says "when did they last touch the API?"), and
both are NULL-safe / DEFAULT-safe so existing rows backfill atomically
without app-side coordination.

``user.is_active`` is ``BOOLEAN NOT NULL DEFAULT TRUE`` (Decision I §1605):
the existing ``admin`` + ``agent`` rows seeded by ``seed_admin()`` plus any
``member`` rows seeded via the register/invite path backfill to TRUE
atomically via the server-side default, so the migration is a null-op for
live data (NFR5-INT-1). The runtime ``is_active = FALSE`` enforcement at
``POST /api/auth/login`` + ``POST /api/auth/refresh`` is owned by Story
8.3 per epics §1786, NOT here — Story 8.1 ships the column with the
TRUE default; 8.3 ships the deactivation flow.

``user.last_active_at`` is ``DATETIME NULL`` (Decision I §1606): no server
default. Populated only by ``LastActiveMiddleware`` (apps/api/app/core/
auth/middleware.py, shipped in this same story); existing rows stay NULL
until the user makes their first authenticated request. NULL is the
documented "never been active or activity unknown" sentinel; the admin
Users tab (Story 8.2) renders NULL as "—" rather than special-casing.

No new table; no new index. The two columns are part of the existing
``user`` table and have no per-column query pattern that warrants an
index in Initiative 5 (the admin Users tab paginates over the full user
list and sorts by ``last_active_at DESC`` in app-side Python after the
LIMIT/OFFSET window, not via index).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_users_is_active_last_active"
down_revision = "0013_users_2fa_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "user",
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "last_active_at")
    op.drop_column("user", "is_active")
