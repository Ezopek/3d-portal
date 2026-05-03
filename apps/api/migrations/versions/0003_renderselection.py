"""renderselection table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "renderselection",
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column("selected_paths", sa.String(), nullable=False),
        sa.Column("set_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("set_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("renderselection")
