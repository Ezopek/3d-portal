"""Add the browse-category schema: browse_category + model_browse_category (additive).

Revision ID: 0020_browse_categories
Revises: 0019_drop_category
Create Date: 2026-07-26

Initiative 26 / Epic 49 Story 49.1 (Decisions AX — data model, AZ — migration
posture). Creates the two NEW browse-category tables and ships ATOMICALLY with
the ORM entities ``BrowseCategory`` + ``ModelBrowseCategory`` in the same commit:
``tests/test_orm_migration_parity.py`` asserts ``compare_metadata`` is an empty
diff between the migration-upgraded schema and ``SQLModel.metadata``, so an
entities-only branch and a migration-only branch each fail the merge gate. The
two halves are therefore not independently mergeable.

STRUCTURAL ONLY — no seed content. ``upgrade()`` inserts ZERO rows; the governed
starter categories are an idempotent admin-run seed owned by Story 49.2 (the
same content-out-of-schema split Story 41.3 established). Model↔category
assignments ship empty; a Model with zero categories is valid and stays public.

NO EXISTING TABLE IS TOUCHED — no ``batch_alter_table`` anywhere. ``batch_alter_table``
appears in 0018/0019 only because SQLite needs a table copy to alter an EXISTING
table; 0020 alters nothing, so it needs none.

NO RETIRED NAME IS REUSED. 0019_drop_category dropped ``category`` and
``model.category_id``; this migration creates the distinct ``browse_category`` /
``model_browse_category`` and does NOT revert, edit, or re-order 0019. The
Initiative 25 retirement of the mandatory single category stands.

WHY ``downgrade()`` IS IMPLEMENTED HERE — a deliberate departure from 0018/0019,
recorded so a future reader does not "fix" it into a ``raise NotImplementedError``
for false consistency: 0019 is forward-only because it DESTROYS pre-existing
production data (a dropped table cannot be restored by Alembic). 0020 destroys
nothing — it only creates two brand-new, initially empty tables, so dropping
them again is a genuinely safe and complete rollback. Making it raise would
discard a real rollback path for zero honesty gain. Per Decision AZ this is
explicitly NOT a destructive gate: the 0019 destructive-go protocol does not
apply, and the standing pre-deploy backup policy is sufficient. Before dropping
either table, ``downgrade()`` nulls ``browse_category.parent_id``: this bounded
DML disarms SQLite's self-referential RESTRICT constraint only for rows in the
table that the downgrade immediately removes.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020_browse_categories"
down_revision = "0019_drop_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # browse_category — column shapes mirror _entities.py BrowseCategory and the
    # 0018 idiom: sa.Uuid(as_uuid=True) PK, sa.String() text columns,
    # sa.Integer(nullable=False, server_default="0") for the positional int, and
    # sa.DateTime(), nullable=False with NO server_default for timestamps (the
    # ORM supplies them via default_factory=_now_utc).
    op.create_table(
        "browse_category",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_pl", sa.String(), nullable=True),
        sa.Column("description_en", sa.String(), nullable=True),
        sa.Column("description_pl", sa.String(), nullable=True),
        sa.Column("inclusion_criterion", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        # Self-referential FK (0004:21-30 proves the shape works on SQLite).
        # Nullable: the MVP taxonomy is flat, and the depth-2 ceiling is a
        # SERVICE-layer rule (Story 49.5), never expressed in DDL.
        sa.Column(
            "parent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("browse_category.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    # Index name MUST be exactly uq_browse_category_slug to match the ORM's
    # explicit Index(...) — a Field(unique=True, index=True) declaration would
    # auto-name it ix_browse_category_slug and drift the parity gate. Slug
    # uniqueness is GLOBAL, not per-parent.
    op.create_index("uq_browse_category_slug", "browse_category", ["slug"], unique=True)

    # model_browse_category (M:N) — the 0004:142-158 model_tag idiom verbatim:
    # composite PK across both FK columns, model CASCADE, category RESTRICT.
    op.create_table(
        "model_browse_category",
        sa.Column(
            "model_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("browse_category.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    # Reverse-direction index: the composite PK already covers
    # (model_id, category_id); this covers category-first lookups
    # ("which models are in this category").
    op.create_index(
        "ix_model_browse_category_cat_model",
        "model_browse_category",
        ["category_id", "model_id"],
    )


def downgrade() -> None:
    # Disarm the INTERNAL self-FK before any drop. DROP TABLE performs an
    # implicit per-row delete on SQLite, and browse_category.parent_id is
    # ON DELETE RESTRICT against browse_category itself — so with any parent/
    # child pair present and PRAGMA foreign_keys=ON, "DROP TABLE
    # browse_category" raises "FOREIGN KEY constraint failed". WITHOUT this
    # UPDATE that failure was also unrecoverable — counterfactual, describing
    # the pre-fix body and the RED actually observed for it, NOT this one: the
    # drops then ran outside any transaction and autocommitted, so the abort
    # left a permanently half-reverted schema (browse_category alive without
    # uq_browse_category_slug, model_browse_category already destroyed). With
    # the UPDATE first that no longer holds here: it is DML, so on the supported
    # online path pysqlite opens an implicit transaction which the drops below
    # then share. Alembic's own engine (migrations/env.py, engine_from_config)
    # never issues the pragma today, but this revision must not depend on that
    # staying true.
    #
    # These rows belong to a table this very statement block is about to
    # delete, so nulling parent_id loses NO surviving data — it only removes
    # the ordering constraint between rows that are all going away.
    op.execute("UPDATE browse_category SET parent_id = NULL WHERE parent_id IS NOT NULL")

    # Reverse of upgrade(), child table before parent so the RESTRICT FK on
    # model_browse_category.category_id never blocks the drop. Safe and complete:
    # both tables are created by this revision, so nothing pre-existing is lost.
    op.drop_index("ix_model_browse_category_cat_model", table_name="model_browse_category")
    op.drop_table("model_browse_category")
    op.drop_index("uq_browse_category_slug", table_name="browse_category")
    op.drop_table("browse_category")
