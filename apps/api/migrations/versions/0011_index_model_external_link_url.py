"""Add index on model_external_link.url for the TB-004 dedup filter.

Revision ID: 0011_index_model_external_link_url
Revises: 0010_drop_model_legacy_id
Create Date: 2026-05-12

TB-004 (commit `afaa847`) added a `?external_url=<url>` query parameter
to `GET /api/models` that subqueries `ModelExternalLink.url`. The
column had no index — the subquery was a full table scan. Tolerable
at homelab scale (~200 rows on 2026-05-12) but not under any future
bulk-import sweep (e.g. Story 4.6 CLI mass-onboarding). TB-008 surfaced
this from the TB-004 adversarial review (P2 #3, confidence 82).

Non-unique because a given URL can in theory appear on multiple
`source`/`model_id` rows in edge cases (manually curated duplicate
links, or two models sharing a single Printables source).

SQLite supports `CREATE INDEX` directly without `batch_alter_table`
for additive index changes — kept consistent with 0009 (which also
added indexes without the batch wrapper).
"""

from __future__ import annotations

from alembic import op

revision = "0011_index_model_external_link_url"
down_revision = "0010_drop_model_legacy_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_model_external_link_url",
        "model_external_link",
        ["url"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_model_external_link_url", table_name="model_external_link")
