"""2FA columns on users + recovery_codes table for Initiative 5 / Epic 7.

Revision ID: 0013_users_2fa_columns
Revises: 0012_invite_tokens
Create Date: 2026-05-19

Initiative 5 (E7) TOTP 2FA primitives. Architecture decisions D (users
column additions + Fernet boundary) and E (recovery_codes table +
bcrypt-at-rest + batch lifecycle) materialized as a single migration
because both target the same enrollment milestone — adding the columns
without the table (or vice-versa) leaves Decision D / E partially
observable on disk, which we avoid for the same reason Story 6.1
shipped 0012 as one migration rather than two.

``user.totp_secret`` is ``VARCHAR(255) NULL`` (Fernet ciphertext slot;
NULL = no TOTP configured). ``user.totp_enabled_at`` is
``DateTime NULL`` (NULL = 2FA inactive; ``IS NOT NULL`` = the login
flow will extend with a second factor per Story 7.3). Both default to
NULL, so the existing ``admin`` + ``agent`` rows seeded by
``seed_admin()`` migrate without backfill — NFR5-INT-1's "null-op
migration for the agent service account" property holds by
construction.

``recovery_codes`` uses the same Init 0 UUID + ``user.id`` FK shape as
``invite_tokens`` (UUID PK, ``user.id`` singular table FK with
``ondelete=CASCADE`` — when an admin deletes a user, every recovery
code row for that user vanishes too; bcrypt-hashed codes are
credential-equivalent and have no audit purpose detached from the
user). The two non-unique indexes match Decision E §1519-1531 verbatim:
``ix_recovery_codes_user_id`` for the per-user verify-iteration query
(Story 7.3's "iterate active batch where ``invalidated_at IS NULL``")
and ``ix_recovery_codes_batch_id`` for the batch lifecycle query
(Story 7.5's batch invalidation on regenerate / disable).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_users_2fa_columns"
down_revision = "0012_invite_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("totp_secret", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("totp_enabled_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "recovery_codes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(length=60), nullable=False),
        sa.Column("batch_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_recovery_codes_user_id",
        "recovery_codes",
        ["user_id"],
    )
    op.create_index(
        "ix_recovery_codes_batch_id",
        "recovery_codes",
        ["batch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_recovery_codes_batch_id", table_name="recovery_codes")
    op.drop_index("ix_recovery_codes_user_id", table_name="recovery_codes")
    op.drop_table("recovery_codes")
    op.drop_column("user", "totp_enabled_at")
    op.drop_column("user", "totp_secret")
