"""Drop Model.legacy_id column and its unique index.

Revision ID: 0010_drop_model_legacy_id
Revises: 0009
Create Date: 2026-05-11

Executes the Story 4.4 decision (DROP) documented in
`docs/migration-reports/2026-05-11-legacy-sot-folder-decision.md`.

The legacy_id column was set on every row migrated from the file-based
catalog (`_index/index.json`) at the 2026-05-04 cutover. Audit-log query
(2026-05-11) confirmed zero post-cutover writes to the column. The only
remaining runtime read was `apps/api/scripts/hydrate_local_tree.py:305`
(folder-naming suffix), retired in the same followup story by switching
to a short-uuid suffix.

Pre-drop mapping is preserved in
`docs/migration-reports/2026-05-11-legacy-id-snapshot.json` (89 rows,
committed to git as a permanent cross-reference artifact).

SQLite requires `batch_alter_table` for column drops (per the project's
established convention — see 0004, 0005, 0006, 0007).
"""

from __future__ import annotations

from alembic import op

revision = "0010_drop_model_legacy_id"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model") as batch_op:
        batch_op.drop_index("ix_model_legacy_id")
        batch_op.drop_column("legacy_id")


def downgrade() -> None:
    """Re-add the column + index. Existing data is NOT restored — operator
    would have to re-import from `docs/migration-reports/2026-05-11-
    legacy-id-snapshot.json` manually after a downgrade."""
    import sqlalchemy as sa

    with op.batch_alter_table("model") as batch_op:
        batch_op.add_column(sa.Column("legacy_id", sa.String(), nullable=True))
        batch_op.create_index("ix_model_legacy_id", ["legacy_id"], unique=True)
