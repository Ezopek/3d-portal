"""Drop legacy tables: thumbnailoverride and renderselection.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-06

Both tables predate the SoT refactor and reference models by their
legacy 3-digit string ID (e.g. "001"). After the refactor:

- ThumbnailOverride is replaced by Model.thumbnail_file_id (UUID FK to ModelFile).
- RenderSelection is replaced by ModelFile.selected_for_render (per-row bool).

The path-based override / selection rows are no longer read or written
by any live code. Drop the tables so the schema reflects reality.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("renderselection")
    op.drop_table("thumbnailoverride")


def downgrade() -> None:
    op.create_table(
        "thumbnailoverride",
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column("relative_path", sa.String(), nullable=False),
        sa.Column("set_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("set_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "renderselection",
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column("selected_paths", sa.String(), nullable=False),
        sa.Column("set_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("set_at", sa.DateTime(), nullable=False),
    )
