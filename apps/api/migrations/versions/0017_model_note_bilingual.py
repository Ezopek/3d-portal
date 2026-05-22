"""Add body_pl + body_en columns to model_note (bilingual description schema).

Revision ID: 0017_model_note_bilingual
Revises: 0016_refresh_token_revoke_reasons_e8
Create Date: 2026-05-22

Initiative 10 Story 16.1 + Architecture Decision L. Adds nullable
``body_pl`` + ``body_en`` columns to ``model_note`` so description-kind
notes can carry both Polish and English content. Backfills
``body_en`` from existing ``body`` for description rows (existing catalog
content is English-source-dominant). Leaves ``body`` populated for
backward compatibility — non-description notes (``print_settings`` etc.)
continue to use it; description rows have both ``body`` (legacy mirror)
and ``body_en`` (new canonical) until a future cleanup migration drops
the legacy mirror.

Forward-only migration acceptable per NFR10-SCHEMA-MIGRATION-1 (catalog
is single-instance, <2-min downtime acceptable). Down-migration drops
``body_pl`` + ``body_en``; description-kind rows fall back to ``body``
which was never cleared.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_model_note_bilingual"
down_revision = "0016_refresh_token_revoke_reasons_e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_note") as batch:
        batch.add_column(sa.Column("body_pl", sa.String(), nullable=True))
        batch.add_column(sa.Column("body_en", sa.String(), nullable=True))

    # Backfill: copy existing body → body_en for description-kind rows only.
    # Non-description notes (print_settings etc.) keep using `body` exclusively.
    op.execute(
        """
        UPDATE model_note
           SET body_en = body
         WHERE kind = 'description'
           AND body_en IS NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("model_note") as batch:
        batch.drop_column("body_en")
        batch.drop_column("body_pl")
