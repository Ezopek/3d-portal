"""new entity tables: category, tag, model, model_file, model_tag,
model_print, model_external_link, model_note

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # category (self-FK)
    op.create_table(
        "category",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "parent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("category.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_pl", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("parent_id", "slug", name="uq_category_parent_slug"),
    )
    op.create_index("ix_category_parent", "category", ["parent_id"])
    op.create_index("ix_category_slug", "category", ["slug"])
    # Partial unique index for root-level categories (parent_id IS NULL).
    # ANSI SQL treats NULL != NULL, so the composite UniqueConstraint above
    # does not catch two root categories (parent_id IS NULL) with the same slug.
    # Both SQLite (>=3.8.9) and Postgres support partial unique indexes.
    op.create_index(
        "uq_category_root_slug",
        "category",
        ["slug"],
        unique=True,
        sqlite_where=sa.text("parent_id IS NULL"),
        postgresql_where=sa.text("parent_id IS NULL"),
    )

    # tag
    op.create_table(
        "tag",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_pl", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tag_slug", "tag", ["slug"])

    # model (no thumbnail_file_id yet — added below after model_file exists)
    op.create_table(
        "model",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("legacy_id", sa.String(), nullable=True, unique=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_pl", sa.String(), nullable=True),
        sa.Column(
            "category_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("category.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source", sa.String(), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(), nullable=False, server_default="not_printed"),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("date_added", sa.Date(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "rating IS NULL OR (rating BETWEEN 1.0 AND 5.0)",
            name="ck_model_rating_range",
        ),
    )
    op.create_index("ix_model_category_id", "model", ["category_id"])
    op.create_index("ix_model_status", "model", ["status"])
    op.create_index("ix_model_deleted_at", "model", ["deleted_at"])
    op.create_index("ix_model_legacy_id", "model", ["legacy_id"])
    op.create_index("ix_model_slug", "model", ["slug"])

    # model_file
    op.create_table(
        "model_file",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("original_name", sa.String(), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=False, unique=True),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "model_id",
            "sha256",
            "kind",
            name="uq_model_file_model_sha_kind",
        ),
    )
    op.create_index("ix_model_file_model_id", "model_file", ["model_id"])
    op.create_index("ix_model_file_sha256", "model_file", ["sha256"])

    # add model.thumbnail_file_id now that model_file exists
    with op.batch_alter_table("model") as batch_op:
        batch_op.add_column(
            sa.Column(
                "thumbnail_file_id",
                sa.Uuid(as_uuid=True),
                nullable=True,
            ),
        )
        batch_op.create_foreign_key(
            "fk_model_thumbnail_file_id",
            "model_file",
            ["thumbnail_file_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # model_tag (M2M)
    op.create_table(
        "model_tag",
        sa.Column(
            "model_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tag.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_model_tag_tag_model", "model_tag", ["tag_id", "model_id"])

    # model_print
    op.create_table(
        "model_print",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "photo_file_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model_file.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("printed_at", sa.Date(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_model_print_model_id", "model_print", ["model_id"])

    # model_external_link
    op.create_table(
        "model_external_link",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "model_id",
            "source",
            name="uq_model_external_link_model_source",
        ),
    )
    op.create_index(
        "ix_model_external_lookup",
        "model_external_link",
        ["source", "external_id"],
    )

    # model_note
    op.create_table(
        "model_note",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_model_note_model_kind", "model_note", ["model_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_model_note_model_kind", table_name="model_note")
    op.drop_table("model_note")
    op.drop_index("ix_model_external_lookup", table_name="model_external_link")
    op.drop_table("model_external_link")
    op.drop_index("ix_model_print_model_id", table_name="model_print")
    op.drop_table("model_print")
    op.drop_index("ix_model_tag_tag_model", table_name="model_tag")
    op.drop_table("model_tag")
    with op.batch_alter_table("model") as batch_op:
        batch_op.drop_column("thumbnail_file_id")
    op.drop_index("ix_model_file_sha256", table_name="model_file")
    op.drop_index("ix_model_file_model_id", table_name="model_file")
    op.drop_table("model_file")
    op.drop_index("ix_model_slug", table_name="model")
    op.drop_index("ix_model_legacy_id", table_name="model")
    op.drop_index("ix_model_deleted_at", table_name="model")
    op.drop_index("ix_model_status", table_name="model")
    op.drop_index("ix_model_category_id", table_name="model")
    op.drop_table("model")
    op.drop_index("ix_tag_slug", table_name="tag")
    op.drop_table("tag")
    op.drop_index("uq_category_root_slug", table_name="category")
    op.drop_index("ix_category_slug", table_name="category")
    op.drop_index("ix_category_parent", table_name="category")
    op.drop_table("category")
