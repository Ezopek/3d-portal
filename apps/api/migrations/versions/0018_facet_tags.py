"""Add facet-tag schema: tag_group table + tag.group_id/group_position (additive).

Revision ID: 0018_facet_tags
Revises: 0017_model_note_bilingual
Create Date: 2026-07-18

Initiative 25 / Epic 41 Story 41.2. Brings the Alembic production schema into
parity with the facet-tag ORM landed in 41.1: creates ``tag_group`` and adds
``tag.group_id`` / ``tag.group_position`` (FK ``tag.group_id`` -> ``tag_group.id``,
ON DELETE SET NULL). Purely additive and fully reversible.

DEFERRED — the destructive category retirement is intentionally NOT in this
migration. The original 0018 sketch also dropped ``model.category_id`` +
``category`` (forward-only). That destructive DDL is deferred to the E42 backend
cut-over and must land in the SAME migration/commit as the ORM removal of
``class Category`` + ``Model.category_id`` (suggested ``0019_drop_category``).
Reason: prod applies ``alembic upgrade head`` against the HEAD-built image on any
deploy (docs/operations.md:234); a forward-only destructive migration on ``main``
before the ORM/app ``Category`` references are gone would irrecoverably brick prod
catalog/share (a dropped table + a raising ``downgrade`` cannot be recovered by
re-deploying the prior image). Keeping 0018 additive + reversible preserves
"main deployable at every commit" and ORM<->migration parity across E41->E47.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_facet_tags"
down_revision = "0017_model_note_bilingual"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tag_group — column shapes mirror _entities.py:61-77 and the 0004 idiom
    # (UUID PK via sa.Uuid(as_uuid=True); timestamps nullable=False with no
    # server_default — the ORM supplies values via default_factory=_now_utc).
    op.create_table(
        "tag_group",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_pl", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    # Index name MUST be exactly uq_tag_group_slug to match the ORM
    # (_entities.py:66) and satisfy the drift-guard deferred from 41.1.
    op.create_index("uq_tag_group_slug", "tag_group", ["slug"], unique=True)

    # Additive-only: model / model.category_id / category are intentionally
    # untouched here. The destructive category-retirement DDL is deferred to the
    # E42 cut-over (must land atomically with the ORM removal of Category); a
    # forward-only destructive migration on main before then bricks prod on
    # `alembic upgrade head` and is unrecoverable. See module docstring.
    # batch_alter_table is required on SQLite to add a FK to an existing table.
    with op.batch_alter_table("tag") as batch:
        batch.add_column(sa.Column("group_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.add_column(
            sa.Column("group_position", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_foreign_key(
            "fk_tag_group_id",
            "tag_group",
            ["group_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    # Reverse of upgrade(). The batch table-copy removes the inline FK together
    # with group_id (precedent 0010:36-38, 0005:125-126) — no drop_constraint.
    with op.batch_alter_table("tag") as batch:
        batch.drop_column("group_position")
        batch.drop_column("group_id")
    op.drop_index("uq_tag_group_slug", table_name="tag_group")
    op.drop_table("tag_group")
