"""Drop the legacy category taxonomy: model.category_id + category table.

Revision ID: 0019_drop_category
Revises: 0018_facet_tags
Create Date: 2026-07-22

Initiative 25 / Epic 47 Story 47.5 — the terminal, destructive category
retirement (Decision AV / NFR25-SCHEMA-MIGRATION-1). Facet tags (E41-E46) are
the sole classification system; this migration removes the last DB remnant of
the single-category taxonomy in the SAME commit as the ORM removal of the
Category entity and the model FK column (parity enforced by the T-PAR test).

Structural only — no data copy, no seed content. The live rows it deletes
(operator-authorized: GO E47 ATOMIC CUTOVER, 2026-07-22) are recoverable only
via the pre-deploy backup + whole-commit git revert, never via Alembic
downgrade (forward-only; ``downgrade()`` raises).
"""

from __future__ import annotations

from alembic import op

revision = "0019_drop_category"
down_revision = "0018_facet_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model") as batch:
        batch.drop_index("ix_model_category_id")
        batch.drop_column("category_id")  # NO drop_constraint — the category.id FK
        # is an unnamed inline (0004:73-78); the
        # SQLite batch table-copy removes it.
    op.drop_table("category")  # self-FK + uq_category_parent_slug +
    # uq_category_root_slug + ix_category_parent
    # + ix_category_slug die with the table.


def downgrade() -> None:
    raise NotImplementedError(
        "0019_drop_category is forward-only (Decision AV / NFR25-SCHEMA-MIGRATION-1)"
    )
