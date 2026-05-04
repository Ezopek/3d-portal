"""user PK to UUID, replace auditevent with audit_log,
add model_note.author_id, retype legacy FKs to user.

Destructive: drops existing user, auditevent, thumbnailoverride,
renderselection rows. Acceptable for dev (.190); admin re-seeded at
startup; tokens invalidated; thumbnail/render selections re-set via UI.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- DESTRUCTIVE: drop legacy tables in reverse-dependency order ---
    # Tables with FK to user must drop before user.
    op.drop_table("renderselection")
    op.drop_table("thumbnailoverride")
    op.drop_table("auditevent")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")

    # --- Recreate user with UUID PK ---
    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    # --- Recreate thumbnailoverride with UUID FK ---
    op.create_table(
        "thumbnailoverride",
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column("relative_path", sa.String(), nullable=False),
        sa.Column(
            "set_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("set_at", sa.DateTime(), nullable=False),
    )

    # --- Recreate renderselection with UUID FK ---
    op.create_table(
        "renderselection",
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column("selected_paths", sa.String(), nullable=False),
        sa.Column(
            "set_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("set_at", sa.DateTime(), nullable=False),
    )

    # --- Create audit_log (replaces auditevent) ---
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("before_json", sa.String(), nullable=True),
        sa.Column("after_json", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_at", "audit_log", ["at"])
    op.create_index(
        "ix_audit_log_entity",
        "audit_log",
        ["entity_type", "entity_id", "at"],
    )
    op.create_index(
        "ix_audit_log_actor",
        "audit_log",
        ["actor_user_id", "at"],
    )

    # --- Add model_note.author_id (FK to new UUID user) ---
    with op.batch_alter_table("model_note") as batch_op:
        batch_op.add_column(
            sa.Column(
                "author_id",
                sa.Uuid(as_uuid=True),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_model_note_author_id",
            "user",
            ["author_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    # Reverse-order drop, recreating int-id legacy state.
    with op.batch_alter_table("model_note") as batch_op:
        batch_op.drop_column("author_id")

    op.drop_index("ix_audit_log_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_index("ix_audit_log_at", table_name="audit_log")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_table("renderselection")
    op.drop_table("thumbnailoverride")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")

    # Recreate legacy int-id user
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    # Recreate legacy auditevent (with int FK)
    op.create_table(
        "auditevent",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("user.id"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload", sa.String(), nullable=False),
    )
    op.create_index("ix_auditevent_at", "auditevent", ["at"])
    op.create_index("ix_auditevent_kind", "auditevent", ["kind"])

    # Recreate legacy thumbnailoverride with int FK
    op.create_table(
        "thumbnailoverride",
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column("relative_path", sa.String(), nullable=False),
        sa.Column(
            "set_by_user_id",
            sa.Integer(),
            sa.ForeignKey("user.id"),
            nullable=False,
        ),
        sa.Column("set_at", sa.DateTime(), nullable=False),
    )

    # Recreate legacy renderselection with int FK
    op.create_table(
        "renderselection",
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column("selected_paths", sa.String(), nullable=False),
        sa.Column(
            "set_by_user_id",
            sa.Integer(),
            sa.ForeignKey("user.id"),
            nullable=False,
        ),
        sa.Column("set_at", sa.DateTime(), nullable=False),
    )
