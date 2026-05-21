"""Extend ck_refresh_tokens_revoke_reason to admit Epic 8 admin actions.

Revision ID: 0016_refresh_token_revoke_reasons_e8
Revises: 0015_users_force_2fa_enrollment
Create Date: 2026-05-20

Discovered via Story 9.2 scenario execution (six-scenario audit coverage):
Story 8.3 (admin user deactivation) writes ``revoke_reason="force_deactivation"``
at apps/api/app/modules/admin/router.py:306; Story 8.3 admin force-logout
writes ``revoke_reason="admin_force_logout"`` at apps/api/app/modules/admin/
router.py:374. Both values fail the existing CHECK constraint emitted by
migration 0009 (allowed: rotated / logout / logout_all / reuse_detected /
manual). On admin invocation the INSERT/UPDATE raises sqlite3.IntegrityError
mid-transaction and the admin's PATCH/POST returns HTTP 500.

The audit-discovered scope: admin deactivation + admin force-logout +
admin password-reset force-logout are ALL routed through the same
``r.revoke_reason = "force_deactivation"`` / "admin_force_logout" path.
NFR5-SEC-1 gate condition severity: HIGH (auditor verdict — surface broken
for admin operator; bug shipped to production at 0.1.0+ec5ac5d Story 8.2;
no operator-impact yet because admin-deactivation hasn't been exercised in
real traffic, but the path IS reachable).

Fix: extend the CHECK constraint to the full Epic 8 alphabet.
SQLite cannot ALTER a CHECK constraint in place — must use batch_alter_table
to recreate the table. The new alphabet (lexicographic for stability):
  admin_force_logout, force_deactivation, logout, logout_all, manual,
  reuse_detected, rotated.

Tests: existing apps/api/tests/test_admin_users_mutations.py +
test_admin_force_logout.py + test_admin_password_reset_mint.py — these
DID NOT catch the bug because they ran against a per-test SQLite that
did not have the CHECK constraint enforced under fakeredis client mock
(verified via Story 9.2 reproducer scenario-4 hitting the live .190
deploy where the constraint IS active).
"""

from __future__ import annotations

from alembic import op

revision = "0016_refresh_token_revoke_reasons_e8"
down_revision = "0015_users_force_2fa_enrollment"
branch_labels = None
depends_on = None


_ALLOWED_REASONS_OLD = (
    "rotated",
    "logout",
    "logout_all",
    "reuse_detected",
    "manual",
)

_ALLOWED_REASONS_NEW = (
    "admin_force_logout",
    "force_deactivation",
    "logout",
    "logout_all",
    "manual",
    "reuse_detected",
    "rotated",
)


def _check_clause(reasons: tuple[str, ...]) -> str:
    quoted = ",".join(f"'{r}'" for r in reasons)
    return f"revoke_reason IS NULL OR revoke_reason IN ({quoted})"


def upgrade() -> None:
    with op.batch_alter_table(
        "refresh_tokens",
        recreate="always",
    ) as batch:
        batch.drop_constraint("ck_refresh_tokens_revoke_reason", type_="check")
        batch.create_check_constraint(
            "ck_refresh_tokens_revoke_reason",
            _check_clause(_ALLOWED_REASONS_NEW),
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "refresh_tokens",
        recreate="always",
    ) as batch:
        batch.drop_constraint("ck_refresh_tokens_revoke_reason", type_="check")
        batch.create_check_constraint(
            "ck_refresh_tokens_revoke_reason",
            _check_clause(_ALLOWED_REASONS_OLD),
        )
