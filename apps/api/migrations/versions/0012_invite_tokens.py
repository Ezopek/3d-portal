"""invite_tokens table for Initiative 5 admin-issued invite flow.

Revision ID: 0012_invite_tokens
Revises: 0011_index_ext_link_url
Create Date: 2026-05-19

Initiative 5 (E6) invite-token primitives. Schema mirrors Decision A's
dual-backed pattern (Redis O(1) hot path + DB row that outlives Redis TTL
for the admin audit panel). Decision B's column list is reproduced here
with the Init 0 conventions applied:

* UUID PK + UUID FKs to the singular ``user`` table via the shared
  ``ForeignKey("user.id", ondelete="SET NULL")`` shape. Decision B's
  spec listed ``INTEGER`` ids + ``users.id`` (plural) FKs; both are
  pre-Init-0 holdovers — see Story 6.1 § "Drift 3" for the reconciliation
  rationale.
* ``generated_by_user_id`` is nullable (not ``NOT NULL`` as Decision B
  originally specified) so deleting the admin row does not cascade-delete
  the audit history. Decision A's "DB row outlives Redis TTL" property
  requires the historical view to remain readable after the issuing
  admin is gone.
* Datetimes are plain ``sa.DateTime`` on disk; the SQLModel layer wraps
  reads through ``UTCDateTime`` to re-attach UTC tzinfo for cross-dialect
  Python equality.

Indexes match Decision B verbatim — a single UNIQUE on the token hash
(point-lookup during ``/register`` validation) plus two non-unique
indexes for the admin list view (``generated_at`` for the default sort
order, ``used_by_user_id`` for the per-user invite history join).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_invite_tokens"
down_revision = "0011_index_ext_link_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invite_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "generated_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "used_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("used_from_ip", sa.String(length=45), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ux_invite_tokens_token_hash",
        "invite_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_invite_tokens_generated_at",
        "invite_tokens",
        ["generated_at"],
    )
    op.create_index(
        "ix_invite_tokens_used_by_user_id",
        "invite_tokens",
        ["used_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_invite_tokens_used_by_user_id", table_name="invite_tokens")
    op.drop_index("ix_invite_tokens_generated_at", table_name="invite_tokens")
    op.drop_index("ux_invite_tokens_token_hash", table_name="invite_tokens")
    op.drop_table("invite_tokens")
