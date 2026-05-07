"""refresh_tokens table for cookie-session rotation.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("family_issued_at", sa.DateTime(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("replaced_at", sa.DateTime(), nullable=True),
        sa.Column(
            "replaced_by_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sa.String(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("ip", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.CheckConstraint(
            "revoke_reason IS NULL OR revoke_reason IN "
            "('rotated','logout','logout_all','reuse_detected','manual')",
            name="ck_refresh_tokens_revoke_reason",
        ),
    )
    # TODO: add postgresql_where=... when/if we migrate from SQLite to Postgres.
    op.create_index(
        "ix_refresh_tokens_user_active",
        "refresh_tokens",
        ["user_id"],
        sqlite_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "ix_refresh_tokens_family",
        "refresh_tokens",
        ["family_id"],
    )
    # TODO: add postgresql_where=... when/if we migrate from SQLite to Postgres.
    op.create_index(
        "ux_refresh_tokens_family_active",
        "refresh_tokens",
        ["family_id"],
        unique=True,
        sqlite_where=sa.text("revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_refresh_tokens_family_active", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_active", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
