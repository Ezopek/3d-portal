"""Add position int column to model_file for photo ordering.

Revision ID: 0006_model_file_position
Revises: 0005
Create Date: 2026-05-05

NULL position means "unsorted; use created_at order". Once admin reorders
photos, all photos in that model get assigned positions starting at 0.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_model_file_position"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_file") as batch:
        batch.add_column(sa.Column("position", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("model_file") as batch:
        batch.drop_column("position")
