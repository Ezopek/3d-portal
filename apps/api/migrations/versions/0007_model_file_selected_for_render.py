"""Add selected_for_render bool column to model_file.

Revision ID: 0007
Revises: 0006_model_file_position
Create Date: 2026-05-06

For each model with STL files, the alphabetically (case-insensitive) first
STL is marked selected_for_render=true; everything else stays false. This
mirrors the pre-SoT-refactor behavior where exactly one STL participated in
auto-renders by default and admin could toggle others on explicitly.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006_model_file_position"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_file") as batch:
        batch.add_column(
            sa.Column(
                "selected_for_render",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
    # SQLite cannot easily run a correlated UPDATE with window functions in
    # one statement across versions, so we drive the backfill from Python.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, model_id, original_name "
            "FROM model_file "
            "WHERE kind = 'stl'"
        )
    ).all()
    first_per_model: dict[str, tuple[str, str]] = {}
    for file_id, model_id, original_name in rows:
        key = original_name.lower()
        current = first_per_model.get(model_id)
        if current is None or key < current[1]:
            first_per_model[model_id] = (file_id, key)
    for file_id, _ in first_per_model.values():
        bind.execute(
            sa.text("UPDATE model_file SET selected_for_render = 1 WHERE id = :id"),
            {"id": file_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("model_file") as batch:
        batch.drop_column("selected_for_render")
