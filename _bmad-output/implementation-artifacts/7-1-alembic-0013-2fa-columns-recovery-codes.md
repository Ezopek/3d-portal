# Story 7.1: Alembic migration `0013_users_2fa_columns` + `recovery_codes` table + `TOTP_FERNET_KEY` plumbing

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want a single Alembic migration `apps/api/migrations/versions/0013_users_2fa_columns.py` (chained `down_revision = "0012_invite_tokens"` per Init 0 convention) that (a) adds two nullable columns to the existing singular `user` table — `totp_secret VARCHAR(255) NULL` (Fernet ciphertext slot per architecture.md Decision D §1502, NULL = no TOTP configured) + `totp_enabled_at DATETIME NULL` (NULL = 2FA inactive, `IS NOT NULL` = login flow will branch on Story 7.3 partial-auth path) AND (b) creates the new `recovery_codes` table per Decision E §1519-1531 column spec verbatim (UUID PK + UUID FK to `user.id` ondelete=CASCADE + bcrypt-hashed `code_hash` + shared `batch_id` per enrollment generation cycle + `generated_at` + nullable `used_at` + nullable `invalidated_at`) with the two non-unique indexes Decision E names (`ix_recovery_codes_user_id` for the per-user verify-iteration query + `ix_recovery_codes_batch_id` for the batch lifecycle query), plus three foundational plumbing surfaces required by every downstream Epic 7 story but consumed by NONE of them yet: (c) the `User` SQLModel at `apps/api/app/core/db/models/_user.py` gains the two new nullable fields with the same `UTCDateTime` decorator pattern Init 0 uses elsewhere; (d) a NEW SQLModel class `RecoveryCode` lands in a NEW module `apps/api/app/core/db/models/_recovery.py` (parallel to `_auth.py` for `RefreshToken` — separates the recovery-code lifecycle from the user table same way refresh tokens are separated) and is re-exported from `apps/api/app/core/db/models/__init__.py`; (e) `cryptography>=43` is added as a NEW dependency in `apps/api/pyproject.toml` (replaces the transitive-via-redis-OCSP pull with an explicit first-party dep — `Fernet` is now load-bearing for Init 5 secrets at rest) with `uv lock --check` regenerated in the SAME commit (lesson from Story 6.4 codex fix-up); (f) `TOTP_FERNET_KEY: str` is added as a Pydantic `Settings` field in `apps/api/app/core/config.py` with NO default + a `@model_validator(mode="after")` block that raises `ValueError` on `environment == "production"` AND `TOTP_FERNET_KEY` empty (fail-fast — no unconfigured deployment can boot the API and accidentally write plaintext secrets to disk before encryption is wired); (g) `infra/env.example` documents the key with the inline `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` generation hint; (h) `infra/docker-compose.yml` `services.api.environment` forwards `TOTP_FERNET_KEY: ${TOTP_FERNET_KEY}` (lesson from Story 6.6 + 6.7 repeat compose-env-wiring oversight — promoted to a Story 7.1 mandatory AC, not deferred to Codex fix-up); (i) `apps/api/tests/conftest.py` sets a deterministic test override `os.environ["TOTP_FERNET_KEY"] = "test-fernet-key-32-bytes-base64-url-safe="` so every test in the session has the secret material available without re-deriving; (j) `recovery_code` is added to `apps/api/app/core/audit.py:KNOWN_ENTITY_TYPES` frozenset (Decision: per Decision E §1531 the recovery-code lifecycle is auditable per row — generation, consumption, invalidation — so the audit row keys to the `recovery_codes.id` UUID; reusing the `user` entity_type per `auth.login.*` precedent would lose the per-code traceability that the E7 acceptance drill artifact NFR5-OBS-2 needs; binding decision at spec-creation time per epics.md §1666 — option (a) wins), realizing FR5-2FA-1 foundation (table + Fernet plumbing exist; enrollment endpoint in 7.2) + FR5-AUDIT-1 entity_type half (the 5 E7 action name strings — `auth.totp.enrolled` + `auth.totp.disabled` + `auth.totp.verify.success` + `auth.totp.verify.fail` + `auth.recovery_code.used` — are declared as binding vocabulary in this spec but NOT emitted by any code shipped in Story 7.1; emission happens in 7.2/7.3/7.5/7.5), anchoring architecture.md Decisions D + E exactly + leaving Decision F (`enforce_2fa_for_roles` config flag + fail-fast for `agent` role) for Story 7.4, with the entire diff scoped strictly to schema + types + config + compose env wiring (NO endpoint, NO router, NO frontend, NO `auth/totp/service.py`, NO `pyotp` dependency — all of those land in 7.2+), so that EVERY currently-passing test in `apps/api/tests/` (605-test backend baseline + 326 vitest + 188 Playwright) continues to pass unchanged AND new tests in `apps/api/tests/test_2fa_schema.py` (migration + model + Settings + KNOWN_ENTITY_TYPES coverage) author the binding behavior at the schema layer.

## Acceptance Criteria

**AC-1 — Alembic migration `0013_users_2fa_columns.py` at the correct path `apps/api/migrations/versions/` (NOT `apps/api/alembic/versions/`), chained from `0012_invite_tokens`, adding two nullable User columns + new `recovery_codes` table + 2 indexes; admin + agent rows verify NULL-default post-upgrade.**

- Given the existing `apps/api/migrations/versions/0012_invite_tokens.py` (Story 6.1 — current `alembic upgrade head` target, verified by `alembic current` showing `0012_invite_tokens (head)` on a freshly migrated DB; the `versions/` directory contains exactly 12 migrations 0001–0012 today, no gaps),
- When Story 7.1 ships,
- Then a NEW migration file MUST be created at the EXACT path `apps/api/migrations/versions/0013_users_2fa_columns.py` (NOT `apps/api/alembic/versions/0013_*.py` — doc-drift item 1 from Epic 6 retro; epics.md:1662 says "alembic/versions/" but the live repo path is `migrations/versions/` per `apps/api/alembic.ini:script_location = migrations`). File MUST start with the same docstring + revision-metadata shape as `0012_invite_tokens.py` (mirror the existing precedent verbatim, including the file-leading docstring style and the explicit `from __future__ import annotations` import):

  ```python
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
  ```

- And the `upgrade()` body MUST add the two columns to the existing singular `user` table via `op.add_column` (NOT `batch_alter_table` — SQLite supports `ADD COLUMN` natively for nullable columns, and the precedent of 0009/0010/0011/0012 shows the project uses plain `op.add_column` / `op.create_table` without `batch_alter_table` wrappers):

  ```python
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
  ```

  Binding bullet-points:
  - **Table name `user` (singular).** Init 0 convention; Decision E §1519 was written before the Init 0 convention landed and shows the plural; Story 6.1 already resolved the same drift class for `invite_tokens` (which keeps its plural because it is itself a new table). The FK target uses the live name `user.id`.
  - **`code_hash` length 60.** bcrypt-2b hashes are 60 ASCII chars (`$2b$12$<22-char-salt><31-char-hash>`). Matches `apps/api/app/core/auth/password.py:hash_password()` precedent (the existing `User.password_hash` column is `VARCHAR` with no explicit length on the SQLModel side; here we set 60 explicitly because the column is bcrypt-only and never holds anything else).
  - **`batch_id` is UUID NOT NULL with NO FK.** A batch is a UUID generated at enrollment time and shared across the 8 codes of one generation cycle; there is no separate `batches` table because the batch metadata (generated_at, count, generation reason) is derivable from the recovery_codes rows themselves via GROUP BY batch_id (Decision E §1531 reasoning).
  - **`ondelete="CASCADE"` on `user_id` FK.** Distinct from `invite_tokens.generated_by_user_id` which is `ondelete="SET NULL"` (audit history outlives the admin row). Recovery codes are credential material — when a user is deleted, the codes have no purpose and would be a security liability if retained.
  - **Plain `sa.DateTime`** on disk (no `UTCDateTime` decorator at the Alembic layer — the decorator is a SQLModel read-side wrapper; the migration-time column type stays plain `DateTime` exactly as 0009/0012 precedents demonstrate). The SQLModel layer (AC-3 + AC-4) wraps reads through `UTCDateTime` to re-attach UTC tzinfo for cross-dialect Python equality (identical pattern to `RefreshToken.issued_at`).
  - **Index naming:** `ix_recovery_codes_user_id` + `ix_recovery_codes_batch_id`. Underscored form mirrors the precedent set by `0012`'s `ix_invite_tokens_generated_at` + `ix_invite_tokens_used_by_user_id` (vs the `ux_*` form used for UNIQUE indexes). NO UNIQUE index — bcrypt hashes of 32-bit codes do collide rarely (≤2⁻³² collision per pair) but the user_id+code_hash combination cannot be UNIQUE because two different users could theoretically share a hash; the verify-iteration path filters by user_id first then bcrypt-checks, so no UNIQUE constraint is needed.

- And the `downgrade()` body MUST reverse every step in strict LIFO order (drop indexes → drop table → drop columns):

  ```python
  def downgrade() -> None:
      op.drop_index("ix_recovery_codes_batch_id", table_name="recovery_codes")
      op.drop_index("ix_recovery_codes_user_id", table_name="recovery_codes")
      op.drop_table("recovery_codes")
      op.drop_column("user", "totp_enabled_at")
      op.drop_column("user", "totp_secret")
  ```

  Pattern matches 0012 precedent: explicit `drop_index` calls before `drop_table` (Alembic's `drop_table` does NOT cascade index drops on every backend), then `drop_column` per user-table addition in reverse-add order.

- And running `alembic upgrade head` on a fresh SQLite DB (test fixture path) MUST advance `alembic_version.version_num` from `0012_invite_tokens` to `0013_users_2fa_columns`. Verified by `test_migration_0013_advances_head` (AC-7).

- And after `alembic upgrade head` on a DB that already contains the seeded admin row + (post Story 6.4) one member + (Init 0 baseline) one agent row, all three User rows MUST show `totp_secret IS NULL` AND `totp_enabled_at IS NULL`. Verified by `test_migration_0013_preserves_existing_user_rows_null_default` (AC-7) — this is the verbatim "admin + agent rows verified NULL-default" property from epics.md §1662 + NFR5-INT-1 "null-op migration semantics for agent service account".

- And `alembic downgrade -1` from `0013_users_2fa_columns` back to `0012_invite_tokens` MUST succeed against the same fixture, leaving the `user` table without the two new columns and the `recovery_codes` table dropped. Verified by `test_migration_0013_downgrade_reverses_clean` (AC-7).

**AC-2 — `RecoveryCode` SQLModel at NEW module `apps/api/app/core/db/models/_recovery.py` (parallel to `_auth.py`), re-exported from `__init__.py`, registered on `SQLModel.metadata` for both `alembic upgrade` and the dev/test `init_schema()` `create_all()` path.**

- Given the existing two-surface model-registration pattern documented in `apps/api/app/core/db/models/__init__.py:8-14` (Alembic env.py explicitly imports model modules; `init_schema()` relies on the `__init__.py` re-exports having already been imported at app startup),
- When Story 7.1 ships,
- Then a NEW file MUST be created at `apps/api/app/core/db/models/_recovery.py` with this exact shape:

  ```python
  """Recovery-code table for Initiative 5 / Epic 7 TOTP 2FA.

  Architecture Decision E (architecture.md §1515-1533): eight single-use
  recovery codes generated as a batch at TOTP enrollment, stored as
  bcrypt hashes (defense-in-depth on DB compromise — 32-bit code entropy
  × bcrypt cost 12 yields ≥10⁹ years average crack time per code), with
  per-code lifecycle columns so the audit history can answer "which
  code did Anna consume on 2026-06-12?" and the regenerate-flow (Story
  7.5) can invalidate a whole batch via one UPDATE.

  Story 7.1 ships the schema + model only. Subsequent stories add:

  * ``apps/api/app/modules/auth/totp/service.py`` — batch generation +
    Fernet encrypt helpers (Story 7.2).
  * ``apps/api/app/modules/auth/totp/router.py`` — ``/api/auth/2fa/enroll``
    + ``/api/auth/2fa/enroll/confirm`` + ``/api/auth/2fa/verify`` endpoints
    (Stories 7.2 + 7.3).
  * ``apps/api/app/modules/auth/totp/regenerate_router.py`` — ``/api/auth/
    2fa/recovery-codes/regenerate`` + ``/api/auth/2fa/disable`` (Story 7.5).

  The cleartext code never lives in this table — only its bcrypt digest
  in ``code_hash``. ``batch_id`` is a UUID generated at enrollment time
  and shared across the 8 codes of one generation cycle. The schema
  matches migration 0013_users_2fa_columns 1:1; column-shape changes
  must land in both files in lock-step (same Story 6.1 invite_tokens
  precedent).
  """

  from __future__ import annotations

  import datetime
  import uuid

  from sqlalchemy import Column, Index
  from sqlmodel import Field, SQLModel

  from ._helpers import UTCDateTime, _now_utc, uuid_fk


  class RecoveryCode(SQLModel, table=True):
      """One single-use TOTP recovery code, bcrypt-hashed at rest."""

      __tablename__ = "recovery_codes"
      __table_args__ = (
          Index("ix_recovery_codes_user_id", "user_id"),
          Index("ix_recovery_codes_batch_id", "batch_id"),
      )

      id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
      user_id: uuid.UUID = Field(
          sa_column=uuid_fk("user.id", ondelete="CASCADE", nullable=False),
      )
      code_hash: str = Field(max_length=60)
      batch_id: uuid.UUID
      generated_at: datetime.datetime = Field(
          default_factory=_now_utc,
          sa_column=Column(UTCDateTime, nullable=False),
      )
      used_at: datetime.datetime | None = Field(
          default=None,
          sa_column=Column(UTCDateTime, nullable=True),
      )
      invalidated_at: datetime.datetime | None = Field(
          default=None,
          sa_column=Column(UTCDateTime, nullable=True),
      )
  ```

  Binding bullet-points:
  - **Module placement.** NEW file `_recovery.py` alongside `_auth.py` (`RefreshToken`), NOT in `apps/api/app/modules/auth/totp/models.py` (the `invite_tokens` precedent is `apps/api/app/modules/invite/models.py` which lives in the module directory — DIFFERENT from this case because `invite_tokens` was authored before the module structure stabilized). For Story 7.1, the schema model lives in `core/db/models/_recovery.py` and is imported by `apps/api/app/modules/auth/totp/service.py` (Story 7.2) — same direction as `RefreshToken` → consumed by `apps/api/app/core/auth/refresh.py`.
  - **`UTCDateTime` wrapper on all 3 timestamps.** Matches `RefreshToken` precedent: `Column(UTCDateTime, nullable=False)` for `generated_at`, `Column(UTCDateTime, nullable=True)` for `used_at` + `invalidated_at`. This ensures cross-dialect `datetime.now(UTC)` equality works in SQLite tests and PostgreSQL production.
  - **`uuid_fk("user.id", ondelete="CASCADE", nullable=False)` for user_id.** Uses the existing `_helpers.py:uuid_fk()` factory; the helper returns a `Column` with the right `sa_uuid_type()` and FK shape. The `CASCADE` rationale matches the migration AC-1 rationale: codes are credential material; user-delete cascades.
  - **No `email` / `display_name` / `role` columns.** This is a pure credential-material table; the user reference is by FK only.
  - **No `__init__` overrides; no validators on the model class.** SQLModel defaults (`default_factory=uuid.uuid4`, `default_factory=_now_utc`) are sufficient.

- And `apps/api/app/core/db/models/__init__.py` MUST be updated to import and re-export `RecoveryCode`. The diff is exactly two lines added in alphabetical position:

  ```python
  # (existing) from ._auth import RefreshToken
  from ._recovery import RecoveryCode  # NEW
  # (existing) from ._user import User

  __all__ = [
      "AuditLog",
      ...
      "RecoveryCode",      # NEW (alphabetical between "ModelTag"/"NoteKind" group and "RefreshToken")
      "RefreshToken",
      ...
  ]
  ```

  Precedent: every other model already in `__init__.py` follows the same import-from-private-module + `__all__` extension pattern. The `RecoveryCode` entry slots between `NoteKind` and `RefreshToken` in alphabetical order; the import line is grouped with the other `_<entity>` imports.

- And the model MUST register on `SQLModel.metadata` via mere import (no explicit `metadata.create_all` registration call). Two surfaces verify this:
  - **Alembic autogenerate.** `apps/api/migrations/env.py:9-10` already imports `from app.core.db import models` (the `__init__.py`), so adding `from ._recovery import RecoveryCode` to `__init__.py` is sufficient — Alembic's autogenerate (if ever invoked manually) will see the new table.
  - **`init_schema()` `create_all()` path.** `apps/api/app/core/db/session.py:init_schema()` calls `SQLModel.metadata.create_all(engine)` — also picks up `RecoveryCode` via the same `__init__.py` re-export chain. Story 7.1 verifies via `test_recovery_code_model_registered_on_metadata` (AC-7).

**AC-3 — `User` SQLModel at `apps/api/app/core/db/models/_user.py` gains exactly two new nullable optional fields (`totp_secret`, `totp_enabled_at`) with the `UTCDateTime` wrapper on the timestamp; no field reordering; no `__table_args__` changes; existing tests that construct `User()` via kwargs continue to pass unchanged.**

- Given the existing 26-line `_user.py` (lines 1-26 inclusive: docstring + 6 model fields including `last_login_at: datetime.datetime | None`),
- When Story 7.1 ships,
- Then the file MUST be modified to add exactly two new fields between `password_hash` and `created_at` (group with existing security-credential-style fields). Final shape:

  ```python
  """User table.

  The portal's authentication identity. UUID PK since Slice 1B; the legacy
  int-id User was dropped at the 0005 migration. TOTP 2FA columns added
  by Story 7.1 (migration 0013) — both NULL on the existing admin +
  agent rows so the schema change is null-op for the service account
  (NFR5-INT-1).
  """

  import datetime
  import uuid

  from sqlalchemy import Column
  from sqlmodel import Field, SQLModel

  from ._enums import UserRole
  from ._helpers import UTCDateTime, _now_utc


  class User(SQLModel, table=True):
      __tablename__ = "user"

      id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
      email: str = Field(unique=True, index=True)
      display_name: str
      role: UserRole
      password_hash: str
      totp_secret: str | None = Field(default=None, max_length=255)
      totp_enabled_at: datetime.datetime | None = Field(
          default=None,
          sa_column=Column(UTCDateTime, nullable=True),
      )
      created_at: datetime.datetime = Field(default_factory=_now_utc)
      last_login_at: datetime.datetime | None = None
  ```

  Binding bullet-points:
  - **Both fields are optional with `default=None`.** All existing call sites (`seed.py:14` constructs `User(email=..., display_name=..., role=..., password_hash=...)` with NO totp_* kwargs) continue to work unchanged — Python kwargs + SQLModel `Field(default=None)` accept the absence.
  - **`totp_secret: str | None`** stores Fernet ciphertext when populated. Maximum length 255 matches the migration column shape. The cleartext is NEVER stored on disk — `Fernet.encrypt()` runs at the service-layer enroll-confirm step (Story 7.2).
  - **`totp_enabled_at` uses the `UTCDateTime` wrapper** via `sa_column=Column(UTCDateTime, nullable=True)` — matches the `RefreshToken.replaced_at`/`revoked_at`/`last_used_at` precedent. This is REQUIRED (not just stylistic) because `Story 7.3`'s login flow will compare `user.totp_enabled_at IS NOT NULL` and Story 7.5's disable flow will set it back to `None`; without the UTC wrapper a Postgres `now()` would return tz-aware while SQLite returns naive, breaking equality.
  - **NO field reordering.** Insert the two new fields between `password_hash` and `created_at`. SQLModel field declaration order influences the `CREATE TABLE` column order on a fresh `init_schema()` boot — for consistency with existing test fixtures that compare column ordering this MUST match the migration's `op.add_column` order (totp_secret first, then totp_enabled_at).
  - **NO `__table_args__` change** — no new indexes on the `user` table (Decision D §1502 doesn't index either column; the verify path queries by `id` PK).
  - **The `Column`/`UTCDateTime` imports** are added to the import block (alphabetical: `from sqlalchemy import Column`; the existing `from sqlmodel import Field, SQLModel` line stays unchanged).

- And `apps/api/app/core/db/seed.py:14` MUST NOT be modified — the seed's `User(...)` constructor call relies on `totp_secret=None` + `totp_enabled_at=None` defaults to remain valid (Python passes only the four kwargs it has). Verified by `test_seed_admin_unchanged_after_2fa_columns` (AC-7).

- And the migration MUST be schema-compatible with the SQLModel: a freshly-migrated DB (via `alembic upgrade head`) opened with the updated `User` SQLModel MUST round-trip `User.totp_secret == None` and `User.totp_enabled_at == None` reads without `KeyError` / `AttributeError` / type-mismatch. Verified by `test_user_model_matches_migration_0013_schema` (AC-7).

**AC-4 — `cryptography>=43` added to `apps/api/pyproject.toml` dependencies (FIRST-party dep, replaces transitive-via-redis pull); `uv lock --check` regenerated in the SAME commit; `pyotp` is NOT added in this story (deferred to 7.2).**

- Given the existing 53-line `apps/api/pyproject.toml` (dependencies block lines 5-29, current dep list: fastapi, uvicorn, zxcvbn, arq, pydantic, email-validator, pydantic-settings, sqlmodel, alembic, redis, sentry-sdk[fastapi], bcrypt, pyjwt, python-multipart, httpx, opentelemetry-distro, opentelemetry-exporter-otlp-proto-http, opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-logging, opentelemetry-instrumentation-redis, opentelemetry-instrumentation-sqlalchemy, pillow — 22 deps total; `cryptography` is currently NOT listed even though it ships in the venv as a transitive of redis[hiredis] for OCSP support),
- When Story 7.1 ships,
- Then `pyproject.toml` MUST gain exactly one new dependency line in alphabetical position:

  ```toml
  dependencies = [
      "fastapi>=0.115",
      "uvicorn[standard]>=0.32",
      "zxcvbn>=4.4.28",
      "arq>=0.26",
      "cryptography>=43",        # NEW — Fernet for TOTP secret encryption (Story 7.1, Decision D)
      "pydantic>=2.9",
      ...
  ]
  ```

  Binding bullet-points:
  - **Version pin `>=43`.** Matches the Python 3.12 baseline + the current ecosystem floor (cryptography 43.0+ ships the modern `cryptography.fernet.Fernet` API used in `Settings._block_default_secrets_in_prod`-style validators). Avoids the historical breakage in <42 where `Fernet.generate_key()` returned `bytes` vs the `str` form sometimes assumed by older docs.
  - **Alphabetical placement** between `arq` and `pydantic` keeps the dep list readable. The trailing `# NEW — Fernet ...` comment is intentional Story-7.1 lineage marker (matches the `# Story 6.6 ...` comment style in `config.py:42` + `60`).
  - **NO `pyotp` in this story.** The `pyotp` dependency materializes in Story 7.2 (TOTP secret generation + 6-digit code verification). Adding it here would be scope creep — Story 7.1 only ships the Fernet plumbing because that is needed at the `Settings`-validator-startup layer.

- And `uv.lock` MUST be regenerated in the SAME commit via `uv lock` (run from `apps/api/`). The resulting lockfile MUST contain a `[[package]] name = "cryptography"` block with a pinned version. Verified by `grep '^name = "cryptography"' apps/api/uv.lock | wc -l` returning exactly `1`. This is the lesson from Story 6.4's codex fix-up (uv.lock staleness was the P1 finding; pyproject.toml dep without lockfile regen passed every check-all.sh stage but failed at `docker compose build` on `.190`).

- And `uv lock --check` MUST pass cleanly (exit 0) after the commit. The dev agent's last step before `git add -A && git commit` is `uv lock --check` per project convention A3 (Epic 6 retro Team Agreement A3).

- And the `apps/api/Dockerfile` MUST NOT be modified — the existing `RUN pip install --no-cache-dir .` step (line 16) reads from `pyproject.toml` and picks up the new dep automatically. NO additional system-package install needed for `cryptography` on `python:3.12-slim` (the `build-essential libffi-dev` line 11-12 already covers the FFI compile requirements for the cffi-backed AES primitives in `cryptography` 43.x wheels — and Debian Bookworm slim's `libssl3` is available at runtime).

**AC-5 — `TOTP_FERNET_KEY: str` added to `apps/api/app/core/config.py:Settings` with NO default + `@model_validator(mode="after")` fail-fast on `environment == "production"` AND empty key; tests via `apps/api/tests/test_config.py::test_totp_fernet_key_required_in_production`.**

- Given the existing 116-line `apps/api/app/core/config.py` (Settings class lines 9-110, the existing `# Auth` block lines 34-40, the existing `@model_validator(mode="after") def _block_default_secrets_in_prod` lines 97-110 with the precedent fail-fast pattern for `jwt_secret` + `admin_password`),
- When Story 7.1 ships,
- Then `Settings` MUST gain exactly one new field placed in the `# Auth` block AFTER `admin_password` (groups all auth-related secrets together; ratelimit/observability sections stay below it):

  ```python
  # Auth
  jwt_secret: str = "change-me-in-production"
  jwt_algorithm: str = "HS256"
  jwt_ttl_minutes: int = 10
  cookie_secure: bool = True
  admin_email: str = "admin@local"
  admin_password: str = "change-me"
  totp_fernet_key: str = ""   # NEW — Decision D (Story 7.1). Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

  Binding bullet-points:
  - **Default empty string** `""` (NOT `None`) so the field type stays `str` (matches `jwt_secret` + `admin_password` precedent — those default to `"change-me-in-production"` / `"change-me"` placeholder strings). A literal Fernet-style placeholder default like `"change-me-fernet-key-32-bytes-base64-url-safe="` was considered but rejected: the placeholder would parse cleanly by Fernet's loose base64 validation, so a misconfigured dev environment could silently encrypt with a default key and decrypt later thinking the data is real — empty string forces explicit configuration even in dev.
  - **Field name `totp_fernet_key`** (snake_case) auto-maps to env-var `TOTP_FERNET_KEY` by Pydantic-Settings convention.
  - **NO `Field(...)` wrapper** — plain `str = ""` is the simplest shape and matches the precedent for non-list non-validated string fields in the same class.

- And the existing `_block_default_secrets_in_prod` validator MUST be EXTENDED (NOT replaced; NOT a new validator) to add the `totp_fernet_key` check as a third `if` block. Final shape:

  ```python
  @model_validator(mode="after")
  def _block_default_secrets_in_prod(self) -> "Settings":
      if self.environment == "production":
          if self.jwt_secret == "change-me-in-production":
              raise ValueError(
                  "jwt_secret must be set to a real value in production; "
                  "the default placeholder is not allowed."
              )
          if self.admin_password == "change-me":
              raise ValueError(
                  "admin_password must be set to a real value in production; "
                  "the default placeholder is not allowed."
              )
          if not self.totp_fernet_key:
              raise ValueError(
                  "totp_fernet_key must be set to a real Fernet key in production; "
                  "generate one with: python -c \"from cryptography.fernet import "
                  "Fernet; print(Fernet.generate_key().decode())\". "
                  "An unconfigured TOTP_FERNET_KEY would cause Story 7.2 enroll-confirm "
                  "to silently fail at first 2FA enrollment attempt."
              )
      return self
  ```

  Binding bullet-points:
  - **Third `if` block placed AFTER `admin_password`** (declaration order); the validator method body grows by one block; the validator's docstring is added inline if the dev agent wants to capture the rationale (optional — the validator currently has no docstring; not adding one keeps minimal diff).
  - **Error message includes the literal `python -c` generation command.** Operators see the validator's error in the API container's startup log (lifespan crash) and can copy-paste the command. This is the verbatim shape used in `infra/env.example` (AC-6) — consistent across config.py + env.example.
  - **Fail-fast ONLY in production.** `environment == "dev"` allows empty `totp_fernet_key` to keep the existing dev/test workflow unchanged — the test override in `conftest.py` (AC-8) seeds a deterministic value, and dev work that doesn't touch TOTP doesn't need to set this env-var.
  - **NO format validation of the key contents.** The validator does NOT call `Fernet(self.totp_fernet_key.encode())` to verify the key parses — that runs at first use in Story 7.2's service module. Reason: keeping the validator side-effect-free (no `cryptography` import in config.py) avoids the circular concern + keeps the boot-time check at O(string-truthiness) rather than O(crypto-initialization).

- And the existing module-level imports at the top of `config.py` MUST NOT change — no new `from cryptography...` import is needed (the validator does string-truthiness only). The `cryptography` package becomes a first-party dep per AC-4 but is consumed by Story 7.2's service layer, not by config.py.

- And the `@lru_cache def get_settings()` function (lines 113-115) MUST NOT change — same caching semantics apply to the new field.

**AC-6 — `infra/env.example` documents the new key with the inline generation hint; `infra/docker-compose.yml` `services.api.environment` forwards `TOTP_FERNET_KEY` (lesson from Stories 6.6+6.7 — promoted to mandatory AC at spec-creation time, NOT deferred to Codex fix-up).**

- Given the existing `infra/env.example` (with the `JWT_SECRET=change-me-32-bytes-hex` line at line 8 + the `# Rate-limiting (Story 6.6, ...)` block at lines 13-23 + the existing pattern of inline comments documenting how to generate each secret),
- When Story 7.1 ships,
- Then `infra/env.example` MUST gain exactly one new ACTIVE line (NOT commented-out, because the placeholder serves as the required-configuration prompt — distinct from rate-limit envs which have working defaults) placed immediately after `JWT_SECRET=change-me-32-bytes-hex`:

  ```dotenv
  # API
  ADMIN_EMAIL=admin@local
  ADMIN_PASSWORD=change-me
  JWT_SECRET=change-me-32-bytes-hex
  # TOTP_FERNET_KEY — generate via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  TOTP_FERNET_KEY=
  # COOKIE_SECURE=true   # Set to false only for plain-HTTP local dev
  COOKIE_SECURE=true
  ```

  Binding bullet-points:
  - **Active key=value line** (NOT commented out). Reason: the production fail-fast validator in AC-5 rejects an empty value, so deploying with the example unmodified would surface the failure at API container startup with the explicit generation hint visible in `infra/.env`. A commented-out line would not surface the requirement to operators creating fresh `.env` files.
  - **Generation comment line ABOVE the key.** Mirrors the inline-comment pattern already used at lines 38-44 for the Sentry DSN block. The dev agent MUST NOT replace the existing rate-limit comments — only adds new lines for `TOTP_FERNET_KEY`.

- And `infra/docker-compose.yml` `services.api.environment` block (lines 19-44, ENV map for the `api` service) MUST forward `TOTP_FERNET_KEY` to the container. The new line goes immediately after `JWT_SECRET: ${JWT_SECRET}` (line 23), keeping the auth-related envs grouped:

  ```yaml
      environment:
        ENVIRONMENT: ${ENVIRONMENT}
        ADMIN_EMAIL: ${ADMIN_EMAIL}
        ADMIN_PASSWORD: ${ADMIN_PASSWORD}
        JWT_SECRET: ${JWT_SECRET}
        TOTP_FERNET_KEY: ${TOTP_FERNET_KEY}   # NEW (Story 7.1, Decision D)
        DATABASE_URL: sqlite:////data/state/portal.db
        ...
  ```

  Binding bullet-points:
  - **NO default value** in the compose interpolation (`${TOTP_FERNET_KEY}` without `:-default`). Reason: same as the env.example active-line rationale — operators MUST supply the value, and Pydantic's `_block_default_secrets_in_prod` validator will reject empty values at container startup with a clear error.
  - **Placement: immediately after JWT_SECRET.** Groups with the other auth-secret envs (ADMIN_PASSWORD + JWT_SECRET) for visual clarity in diffs.
  - **`arq-worker` service env block (line 83-) does NOT need TOTP_FERNET_KEY.** The render worker has no auth surface; TOTP is API-only. Verified by `grep` showing no `User` / `auth` imports in `workers/render/`.

- And the lesson from Stories 6.6 + 6.7's repeat compose-env-wiring oversight (Epic 6 retro, "What surprised us" §6 + Action Item §5 + Team Agreement A4) is encoded HERE as a mandatory pre-merge AC, not as a Codex-catch-and-fix-up. The dev agent's pre-commit grep checklist MUST verify: `grep -E 'TOTP_FERNET_KEY' infra/env.example infra/docker-compose.yml apps/api/app/core/config.py apps/api/tests/conftest.py` returns at least one hit per file. If any file is missing the reference, the commit is incomplete.

**AC-7 — New test file `apps/api/tests/test_2fa_schema.py` adds at minimum 12 named test cases covering migration semantics + model registration + Settings validator + KNOWN_ENTITY_TYPES; existing 605-test backend baseline + 326 vitest + 188 Playwright suites continue to pass unchanged.**

- Given the existing `apps/api/tests/conftest.py` `_isolated_db` autouse session fixture (lines 30-58) that runs `init_schema(get_engine())` on the test SQLite DB — this is the surface every schema-related test inherits,
- When Story 7.1 ships,
- Then a NEW test file MUST exist at `apps/api/tests/test_2fa_schema.py` (~250 LOC) with AT LEAST these named test cases (binding names — Dev Agent TDD red-phase checklist):

  | # | Test name | AC | What it asserts |
  |---|-----------|----|-----------------|
  | T1 | `test_migration_0013_advances_head` | AC-1 | Running `alembic upgrade head` on a freshly-created SQLite DB (via `command.upgrade`) advances `alembic_version.version_num` from `0012_invite_tokens` to `0013_users_2fa_columns`. Uses a one-shot temp DB (`Path(tempfile.mkdtemp()) / "alembic.db"`) plus a manually-constructed `alembic.config.Config` pointing at `apps/api/alembic.ini`. |
  | T2 | `test_migration_0013_creates_recovery_codes_table` | AC-1 | Post-upgrade, `sa.inspect(engine).get_table_names()` includes `"recovery_codes"`; the table's column names match exactly `["id", "user_id", "code_hash", "batch_id", "generated_at", "used_at", "invalidated_at"]`; FK from `user_id` to `user.id` has `ondelete="CASCADE"`. |
  | T3 | `test_migration_0013_adds_user_totp_columns` | AC-1 | Post-upgrade, `sa.inspect(engine).get_columns("user")` contains entries for `totp_secret` (`String(255)`, `nullable=True`) and `totp_enabled_at` (`DateTime`, `nullable=True`); no other `user` columns mutate. |
  | T4 | `test_migration_0013_creates_recovery_codes_indexes` | AC-1 | Post-upgrade, `sa.inspect(engine).get_indexes("recovery_codes")` contains both `ix_recovery_codes_user_id` (on `user_id`, `unique=False`) and `ix_recovery_codes_batch_id` (on `batch_id`, `unique=False`). NO UNIQUE indexes on the table. |
  | T5 | `test_migration_0013_preserves_existing_user_rows_null_default` | AC-1 | Seed admin + agent + member rows via raw INSERT pre-upgrade (matching the seed_admin shape but with role variations), run `alembic upgrade head`, then SELECT all three rows: each returns `totp_secret IS None` and `totp_enabled_at IS None`. This is the verbatim "admin + agent rows verified NULL-default" property from epics.md §1662 + NFR5-INT-1. |
  | T6 | `test_migration_0013_downgrade_reverses_clean` | AC-1 | After `alembic upgrade head`, running `alembic downgrade -1` returns the schema to `0012_invite_tokens` state: `recovery_codes` table is gone, `user.totp_secret` + `user.totp_enabled_at` columns are gone. Verified via fresh `sa.inspect(engine)` calls. |
  | T7 | `test_recovery_code_model_registered_on_metadata` | AC-2 | `from app.core.db.models import RecoveryCode` succeeds; `RecoveryCode.__tablename__ == "recovery_codes"`; `RecoveryCode` appears in `SQLModel.metadata.tables`. The model can be instantiated with `RecoveryCode(user_id=uuid.uuid4(), code_hash="$2b$12$..."*1, batch_id=uuid.uuid4())` and the `id` + `generated_at` defaults populate via factories. |
  | T8 | `test_recovery_code_create_round_trip_via_init_schema` | AC-2 | A fresh DB created via `init_schema(engine)` (the non-Alembic path used in dev/tests) MUST register the `recovery_codes` table; insert one row, SELECT it back, assert the round-trip data. This validates that the `__init__.py` re-export wiring (NOT just Alembic) picks up the new model. |
  | T9 | `test_user_model_matches_migration_0013_schema` | AC-3 | After `alembic upgrade head`, the updated `User` SQLModel can read/write `totp_secret` + `totp_enabled_at` on a row without type errors. Insert a User with `totp_secret="ciphertext-placeholder"` + `totp_enabled_at=datetime.now(UTC)`, SELECT it back, assert both fields round-trip correctly (timestamp is tz-aware on read thanks to `UTCDateTime` wrapper). |
  | T10 | `test_seed_admin_unchanged_after_2fa_columns` | AC-3 | `seed_admin(engine, email="admin@local", password="x", display_name="Admin")` still works without modification; the resulting admin row has `totp_secret IS None` and `totp_enabled_at IS None`. Validates that existing call sites do NOT need updating. |
  | T11 | `test_totp_fernet_key_required_in_production` | AC-5 | Setting `ENVIRONMENT=production` + leaving `TOTP_FERNET_KEY` unset (via `monkeypatch.delenv` + `monkeypatch.setenv("ENVIRONMENT", "production")` + `monkeypatch.setenv("JWT_SECRET", "real")` + `monkeypatch.setenv("ADMIN_PASSWORD", "real")` to bypass the other validators) + `get_settings.cache_clear()` + calling `get_settings()` raises `ValidationError` whose message contains the string `"totp_fernet_key must be set"` and the inline `python -c` generation hint. |
  | T12 | `test_totp_fernet_key_empty_ok_in_dev` | AC-5 | The same scenario with `ENVIRONMENT=dev` returns a Settings instance with `totp_fernet_key == ""` and no exception raised. Validates dev/test workflow stays unblocked when the developer hasn't generated a personal Fernet key. |
  | T13 | `test_known_entity_types_includes_recovery_code` | AC-9 | `from app.core.audit import KNOWN_ENTITY_TYPES` returns a frozenset that includes `"recovery_code"`. `record_event(engine, action="auth.recovery_code.used", entity_type="recovery_code", entity_id=uuid.uuid4(), actor_user_id=uuid.uuid4())` does NOT raise `ValueError` — verified by calling `record_event()` directly + reading back the AuditLog row from the DB. |
  | T14 | `test_known_entity_types_count_includes_one_new_addition` | AC-9 | `len(KNOWN_ENTITY_TYPES) == 14` (Story 6.1 added `invite_token` bringing the count to 13; Story 7.1 adds `recovery_code` bringing the count to 14). Guards against accidental duplicate-adds or removal regressions. |

  All test names are binding; the dev agent MAY add additional tests beyond this list but MUST author all 14 named cases verbatim.

- And the test file's import block MUST include:

  ```python
  import datetime
  import tempfile
  import uuid
  from pathlib import Path

  import pytest
  import sqlalchemy as sa
  from alembic import command
  from alembic.config import Config
  from sqlmodel import Session, select

  from app.core.audit import KNOWN_ENTITY_TYPES, record_event
  from app.core.config import Settings, get_settings
  from app.core.db.models import RecoveryCode, User, UserRole
  from app.core.db.seed import seed_admin
  from app.core.db.session import init_schema
  ```

  Binding bullet-points:
  - **Alembic test harness** uses `alembic.command.upgrade` + `alembic.config.Config(str(Path(__file__).parent.parent / "alembic.ini"))` with the test SQLite URL overridden via `config.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_db_path}")`. NO subprocess; runs in-process for speed.
  - **Per-test isolated SQLite** via `pytest.fixture` creating a temp dir + path; the session-scoped `_isolated_db` autouse fixture in `conftest.py` provides the BASE test DB, but migration tests need fresh DBs to avoid mutating the session DB state — author a NEW per-function fixture `_fresh_migration_db` in the test file.
  - **NO fakeredis usage** — Story 7.1 does not touch Redis. `_patch_arq_pool` from conftest.py (autouse) still runs; that's fine and zero-cost.

- And ALL existing test files MUST continue to pass unchanged. Specifically, the dev agent MUST verify post-commit:
  - `pytest apps/api/tests/ -v --tb=short` returns ≥ 619 passed (605 baseline + 14 new — counts vary slightly because the dev agent may add edge-case helpers; exact baseline+new is the constraint).
  - `pytest apps/api/tests/test_share_member_permission.py apps/api/tests/test_ratelimit_middleware.py apps/api/tests/test_ratelimit_share_cap.py -v` returns same count as before (no rate-limit / share-permission regressions from the model + Settings changes).
  - `cd apps/web && npm test -- --run` returns same vitest count as before.
  - `cd apps/web && npx playwright test` returns same Playwright count as before.

**AC-8 — `apps/api/tests/conftest.py` `_isolated_db` autouse fixture sets a deterministic `TOTP_FERNET_KEY` test override so every test has the secret material without re-deriving.**

- Given the existing `_isolated_db` fixture (conftest.py lines 30-58) that sets test-only env-vars (`DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `JWT_SECRET`, `PORTAL_CONTENT_DIR`, `COOKIE_SECURE`) and then calls `get_settings.cache_clear()` + `get_engine.cache_clear()`,
- When Story 7.1 ships,
- Then the same fixture MUST gain exactly one new `os.environ[...]` assignment placed immediately after `os.environ["JWT_SECRET"] = "test-secret-not-real"`:

  ```python
  os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
  os.environ["ADMIN_EMAIL"] = "admin@localhost.localdomain"
  os.environ["ADMIN_PASSWORD"] = "test-admin-pw"
  os.environ["JWT_SECRET"] = "test-secret-not-real"
  # Story 7.1 / Decision D — deterministic Fernet key for TOTP tests.
  # 32 url-safe-base64-encoded bytes; trailing "=" pads to 44 chars total.
  os.environ["TOTP_FERNET_KEY"] = "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="
  os.environ["PORTAL_CONTENT_DIR"] = str(content_dir)
  os.environ["COOKIE_SECURE"] = "false"  # TestClient uses http://testserver (not HTTPS)
  ```

  Binding bullet-points:
  - **Deterministic value `"ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="`** is the base64-encoded ASCII string `fake-test-key-32-bytes-for-tests` (32 chars × 1 byte = 32 bytes, exactly the Fernet key length). Reproducible across test runs without per-session randomization; tests in Story 7.2+ that decrypt TOTP secrets get a stable key.
  - **NO Fernet validation at fixture time.** The string is shape-compatible with Fernet (44 chars, ends with `=`, url-safe-base64) but not actually validated until Story 7.2's `cryptography.fernet.Fernet(key.encode())` constructor is called. If the dev agent in Story 7.2 finds the test key doesn't parse, they can swap it for `Fernet.generate_key().decode()` evaluated once at fixture-creation time — but the deterministic-string variant is preferred for diff-stability.
  - **Placement: between `JWT_SECRET` and `PORTAL_CONTENT_DIR`.** Groups with the other auth-secret env-vars; the order MUST stay this way so an `os.environ.get("TOTP_FERNET_KEY")` call in any test sees the set value.
  - **`get_settings.cache_clear()` already runs in the same fixture (line 46);** the new env-var is picked up on the next `get_settings()` call without additional cache invalidation.

- And the fixture's session scope (`scope="session"` per line 31) means the env-var is set ONCE for the entire test session. This is intentional: tests that want to override `TOTP_FERNET_KEY` per-test (e.g., the `test_totp_fernet_key_required_in_production` test in AC-7 T11) use `monkeypatch.setenv` / `monkeypatch.delenv` + `get_settings.cache_clear()` to override; the session-scope default is the recovery state.

- And NO modification to the `_patch_arq_pool` autouse fixture (lines 13-27) or to the `client` fixture (lines 60-65) is required. Story 7.1 ships zero new endpoints — the `client` fixture continues to spin up a `TestClient(create_app())` without TOTP-related routes attached.

**AC-9 — `apps/api/app/core/audit.py:KNOWN_ENTITY_TYPES` gains exactly one new entry `recovery_code`; the FROZENSET addition mirrors Story 6.1's `invite_token` precedent; existing `record_event(entity_type="user", ...)` callers continue to pass unchanged.**

- Given the existing 44-line `apps/api/app/core/audit.py` with `KNOWN_ENTITY_TYPES` defined as a `frozenset` at lines 28-44 (13 entries: catalog, category, invite_token, model, model_external_link, model_file, model_note, model_print, render_selection, share_token, tag, thumbnail_override, user) + the docstring comment block lines 14-27 listing each entry with its consumption pattern,
- When Story 7.1 ships,
- Then the FROZENSET MUST gain exactly one new entry `recovery_code` in alphabetical position between `render_selection` and `share_token`:

  ```python
  #   recovery_code        — auth.recovery_code.used (entity_id = recovery_codes.id UUID)
  #   render_selection     — admin.render.selection.set/delete (entity_id None: legacy str model_id)
  KNOWN_ENTITY_TYPES: frozenset[str] = frozenset(
      {
          "catalog",
          "category",
          "invite_token",
          "model",
          "model_external_link",
          "model_file",
          "model_note",
          "model_print",
          "recovery_code",        # NEW (Story 7.1, FR5-AUDIT-1 E7 entity)
          "render_selection",
          "share_token",
          "tag",
          "thumbnail_override",
          "user",
      }
  )
  ```

  Binding bullet-points:
  - **Decision: option (a) wins per epics.md §1666.** Add `recovery_code` to the registry rather than reusing `user`. Rationale: Story 7.5's regenerate flow needs queryable per-batch audit history (`SELECT FROM audit_log WHERE entity_type='recovery_code' AND entity_id IN (<batch row IDs>)`). The `user` entity_type would collapse all 8 per-code rows into the same audit lineage as login/logout events, defeating per-code traceability that the NFR5-OBS-2 drill artifact (Story 7.6) needs.
  - **The 5 E7 action names** (`auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`) are NOT registered in any registry — they are free-form strings passed as `action=` kwarg to `record_event()`. This is the verbatim drift-item-2 clarification from Epic 6 retro: `KNOWN_ENTITY_TYPES` is the entity_type registry, NOT an action-name registry. The action vocabulary is documented as a comment in this story's spec + in the upcoming `bmad-correct-course` patch to `prd.md` FR5-AUDIT-1 (already corrected in code; epics.md / prd.md text catches up post-Story-7.1).
  - **Comment line for `recovery_code`** documents the expected `entity_id` shape: the recovery_codes row's UUID PK. This matches the inline comment style at lines 14-27 for every other entry.
  - **The actions `auth.totp.enrolled` / `auth.totp.disabled` / `auth.totp.verify.success` / `auth.totp.verify.fail`** will use `entity_type="user"` (the User row IS the audit subject — these are user-lifecycle events). Only `auth.recovery_code.used` uses `entity_type="recovery_code"` because it has a specific row-level subject. The 4 user-scoped action emissions live in Stories 7.2/7.3 and use the existing `user` entity_type without any further KNOWN_ENTITY_TYPES change.

- And the existing `record_event(entity_type="user", ...)` callers (5+ call sites across `apps/api/app/modules/auth/router.py`, `apps/api/app/modules/invite/router.py`, etc.) MUST continue to pass unchanged. The frozenset addition is additive — no entry is removed or renamed.

- And the validation MUST happen via the existing `if entity_type not in KNOWN_ENTITY_TYPES: raise ValueError(...)` line in `record_event()` (audit.py:67). No changes to the validation logic; just the registry contents.

**AC-10 — Pre-merge `infra/scripts/check-all.sh` is 10/10 green; Codex coverage targets pre-flagged so the dev agent doesn't ship a known fix-up surface.**

- Given the existing 10-stage `infra/scripts/check-all.sh` runner (pre-Epic-6 baseline; stages cover ruff/format/check, pytest, mypy-light, alembic-check, vitest, playwright, docker-compose-build, deploy-skip-gate, etc.; recommended new stages 11+12 from Epic 6 retro action items 5+6 are NOT yet shipped per sprint-status — they are a parallel deferred-quick-dev),
- When Story 7.1 ships,
- Then BEFORE the dev agent runs `git commit`, all 10 existing stages MUST pass cleanly. Specifically:
  - **Stage: ruff format + check** — `apps/api/app/core/config.py` + `apps/api/app/core/db/models/_user.py` + `apps/api/app/core/db/models/_recovery.py` (NEW) + `apps/api/app/core/db/models/__init__.py` + `apps/api/app/core/audit.py` + `apps/api/migrations/versions/0013_users_2fa_columns.py` + `apps/api/tests/conftest.py` + `apps/api/tests/test_2fa_schema.py` (NEW) all pass `ruff format --check .` AND `ruff check .` without warnings.
  - **Stage: pytest backend** — `pytest apps/api/tests/ -v --tb=short` returns ≥ 619 passed (605 baseline + 14 new from AC-7).
  - **Stage: alembic upgrade dry-run** — `alembic upgrade head --sql > /tmp/migration.sql` produces a non-empty SQL emission containing both `ADD COLUMN totp_secret` AND `CREATE TABLE recovery_codes` (verifies that 0013 is the new head; doesn't actually mutate the DB).
  - **Stage: docker-compose build** — `docker compose -f infra/docker-compose.yml build api` succeeds (verifies the new `cryptography` dep installs cleanly on `python:3.12-slim`).

- And the dev agent SHOULD (not MUST — these are deferred quick-dev items per Epic 6 retro Action Items 5 + 6) run the following pre-flight grep checklist verbatim before commit. If any line returns zero hits, the story is incomplete:

  ```bash
  # AC-4 dependency check
  grep -q 'cryptography>=' apps/api/pyproject.toml || echo "FAIL: cryptography missing from pyproject.toml"
  grep -q '^name = "cryptography"' apps/api/uv.lock || echo "FAIL: cryptography missing from uv.lock"

  # AC-5 Settings check
  grep -q 'totp_fernet_key' apps/api/app/core/config.py || echo "FAIL: totp_fernet_key Settings field missing"
  grep -q 'totp_fernet_key must be set' apps/api/app/core/config.py || echo "FAIL: validator missing"

  # AC-6 compose + env wiring (the 6.6+6.7 lesson)
  grep -q 'TOTP_FERNET_KEY' infra/env.example || echo "FAIL: env.example missing TOTP_FERNET_KEY"
  grep -q 'TOTP_FERNET_KEY' infra/docker-compose.yml || echo "FAIL: docker-compose.yml api env missing TOTP_FERNET_KEY"

  # AC-8 conftest override
  grep -q 'TOTP_FERNET_KEY' apps/api/tests/conftest.py || echo "FAIL: conftest test override missing"

  # AC-9 KNOWN_ENTITY_TYPES
  grep -q '"recovery_code"' apps/api/app/core/audit.py || echo "FAIL: recovery_code missing from KNOWN_ENTITY_TYPES"
  ```

  All seven grep lines should produce NO output (silent success). Any FAIL message means the dev agent missed one of the cross-file invariants — same class of defect that Codex caught on Stories 6.6 + 6.7 (compose env wiring).

- And explicit Codex coverage targets — pre-flagged so the dev agent knows what to self-review BEFORE handing off:
  - **uv.lock staleness** (Story 6.4 lesson). Regenerate via `uv lock` in the same commit; verify `uv lock --check` exits 0.
  - **Compose env wiring** (Stories 6.6 + 6.7 lesson). AC-6 makes this a mandatory pre-merge check, not a Codex catch.
  - **OpenAPI contract width** (Story 6.3 lesson). N/A for 7.1 — no new endpoint surface, no OpenAPI delta.
  - **IntegrityError race** (Story 6.4 lesson). N/A for 7.1 — no new INSERT path; the seed_admin race compensation is already in place.
  - **nginx trust-boundary topology** (Story 6.6 lesson). N/A for 7.1 — no IP-keyed surface introduced.
  - **bcrypt hash field length consistency** (NEW concern). `recovery_codes.code_hash` is `VARCHAR(60)` matching bcrypt-2b output. If Story 7.2 chooses bcrypt-2y or a higher cost factor that produces longer hashes, this constraint will need revisiting — flagged here so Story 7.2 spec creation re-verifies.
  - **Fernet key length validation** (NEW concern). Story 7.2 will call `Fernet(settings.totp_fernet_key.encode())`; if the key is not exactly 44 base64-url-safe chars, `cryptography` raises `ValueError` at construction. Story 7.1's `_block_default_secrets_in_prod` validator only checks truthiness — flagged so Story 7.2's service module includes the parse-validation at app-startup or on first use.

**AC-11 — `recovery_codes.code_hash` indexing decision: NO additional index in this story (per-user verify path filters via `ix_recovery_codes_user_id` first, then bcrypt-iterates the ≤8 active codes; adding `ix_recovery_codes_code_hash` would be wasted disk).**

- Given the Story 7.3 verify flow described in epics.md §1691 ("iterate active batch where `invalidated_at IS NULL` calling `bcrypt.checkpw()` for recovery codes — first match sets `used_at`"),
- When the verify path runs at Story 7.3 ship time,
- Then the query plan is: `SELECT * FROM recovery_codes WHERE user_id = ? AND invalidated_at IS NULL` (index seek via `ix_recovery_codes_user_id`) → returns ≤8 rows → iterate `bcrypt.checkpw(submitted, row.code_hash)` in Python. Total: one index seek + ≤8 bcrypt comparisons (~2s worst case per architecture.md §1531). NO query plan benefits from an index on `code_hash` (bcrypt hashes are non-prefix-comparable; lookup is via SCAN, not seek).

- And the decision is encoded explicitly here so a future dev agent on Story 7.5 doesn't reflexively add `ix_recovery_codes_code_hash` (a common reflexive miss).

- And NO UNIQUE constraint on `(user_id, code_hash)`. The bcrypt salt makes hash collisions astronomically unlikely (2⁻³² per pair); the verify path doesn't depend on uniqueness because the batch is ≤8 rows; adding a UNIQUE would only catch a defect (cryptographic salt failure) that the bcrypt library does not allow.

## Tasks / Subtasks

- [x] **T1 — Author Alembic migration `0013_users_2fa_columns.py`** (AC: 1)
  - [x] T1.1 — Create file at EXACT path `apps/api/migrations/versions/0013_users_2fa_columns.py` (NOT `apps/api/alembic/versions/`; doc-drift item 1)
  - [x] T1.2 — Author docstring + revision metadata block matching `0012_invite_tokens.py` style
  - [x] T1.3 — Implement `upgrade()`: `op.add_column("user", totp_secret VARCHAR(255) NULL)` + `op.add_column("user", totp_enabled_at DATETIME NULL)` + `op.create_table("recovery_codes", ...)` + 2 `op.create_index(...)` calls per AC-1 binding code
  - [x] T1.4 — Implement `downgrade()`: drop indexes → drop table → drop columns in strict LIFO order
  - [x] T1.5 — Run `alembic upgrade head` against a fresh SQLite test DB and `alembic_version.version_num` advances to `0013_users_2fa_columns`
  - [x] T1.6 — Run `alembic downgrade -1` and verify clean reversal

- [x] **T2 — Add `RecoveryCode` SQLModel + re-export** (AC: 2)
  - [x] T2.1 — Create NEW file `apps/api/app/core/db/models/_recovery.py` with `RecoveryCode` class matching the migration schema 1:1 (use `UTCDateTime` wrapper for all 3 datetime fields)
  - [x] T2.2 — Update `apps/api/app/core/db/models/__init__.py` to `from ._recovery import RecoveryCode` + add `"RecoveryCode"` to `__all__` in alphabetical position
  - [x] T2.3 — Run `python -c "from app.core.db.models import RecoveryCode; print(RecoveryCode.__tablename__)"` returns `recovery_codes`

- [x] **T3 — Extend `User` SQLModel with 2 nullable optional fields** (AC: 3)
  - [x] T3.1 — Modify `apps/api/app/core/db/models/_user.py`: add `totp_secret: str | None = Field(default=None, max_length=255)` + `totp_enabled_at: datetime.datetime | None = Field(default=None, sa_column=Column(UTCDateTime, nullable=True))` between `password_hash` and `created_at`
  - [x] T3.2 — Add `from sqlalchemy import Column` import; ensure `from ._helpers import UTCDateTime` is in the import block
  - [x] T3.3 — Verify `seed.py:14`'s `User(...)` constructor still works without modification (kwargs accept `totp_*` defaults)

- [x] **T4 — Add `cryptography>=43` dep + regenerate `uv.lock`** (AC: 4)
  - [x] T4.1 — Edit `apps/api/pyproject.toml` to add `"cryptography>=43",` line in alphabetical position between `arq` and `pydantic`
  - [x] T4.2 — Run `cd apps/api && uv lock` to regenerate `apps/api/uv.lock`
  - [x] T4.3 — Verify `uv lock --check` exits 0 (no further regen needed)
  - [x] T4.4 — Verify `grep '^name = "cryptography"' apps/api/uv.lock` returns exactly one hit
  - [x] T4.5 — Run `docker compose -f infra/docker-compose.yml build api` to confirm the new dep installs cleanly on `python:3.12-slim`

- [x] **T5 — Add `TOTP_FERNET_KEY` Settings field + extend production fail-fast validator** (AC: 5)
  - [x] T5.1 — Modify `apps/api/app/core/config.py`: add `totp_fernet_key: str = ""` line in `# Auth` block after `admin_password`
  - [x] T5.2 — Extend `_block_default_secrets_in_prod` validator with a third `if not self.totp_fernet_key: raise ValueError(...)` block including the inline `python -c` generation hint
  - [x] T5.3 — Verify `get_settings()` cache invalidation works as before (no changes to `@lru_cache` semantics)

- [x] **T6 — Wire `TOTP_FERNET_KEY` into `infra/env.example` + `infra/docker-compose.yml`** (AC: 6)
  - [x] T6.1 — Edit `infra/env.example`: add active key line `TOTP_FERNET_KEY=` plus a preceding `# TOTP_FERNET_KEY — generate via: python -c ...` comment, placed immediately after `JWT_SECRET=`
  - [x] T6.2 — Edit `infra/docker-compose.yml`: add `TOTP_FERNET_KEY: ${TOTP_FERNET_KEY}` line in `services.api.environment` block immediately after `JWT_SECRET: ${JWT_SECRET}`
  - [x] T6.3 — Verify NO `TOTP_FERNET_KEY` is added to `services.arq-worker.environment` (worker has no auth surface)

- [x] **T7 — Add `TOTP_FERNET_KEY` deterministic test override to conftest** (AC: 8)
  - [x] T7.1 — Edit `apps/api/tests/conftest.py`: add `os.environ["TOTP_FERNET_KEY"] = "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="` in `_isolated_db` after `JWT_SECRET` line
  - [x] T7.2 — Verify session-scope env-var picked up by every test (`get_settings.cache_clear()` already runs in same fixture)

- [x] **T8 — Add `recovery_code` to `KNOWN_ENTITY_TYPES` frozenset** (AC: 9)
  - [x] T8.1 — Edit `apps/api/app/core/audit.py`: add `"recovery_code",` entry in alphabetical position between `"model_print"` and `"render_selection"` in the `KNOWN_ENTITY_TYPES` frozenset literal
  - [x] T8.2 — Add inline comment `#   recovery_code        — auth.recovery_code.used (entity_id = recovery_codes.id UUID)` to the docstring comment block lines 14-27, in alphabetical position
  - [x] T8.3 — Verify `len(KNOWN_ENTITY_TYPES) == 14` post-change

- [x] **T9 — Author `apps/api/tests/test_2fa_schema.py` with 14 named test cases** (AC: 7)
  - [x] T9.1 — Create file with the import block from AC-7
  - [x] T9.2 — Author per-function fixture `_fresh_migration_db` (per-test temp SQLite + alembic.Config setup)
  - [x] T9.3 — Implement T1-T6 migration tests (AC-1 coverage)
  - [x] T9.4 — Implement T7-T8 model registration tests (AC-2 coverage)
  - [x] T9.5 — Implement T9-T10 User SQLModel + seed_admin tests (AC-3 coverage)
  - [x] T9.6 — Implement T11-T12 Settings validator tests (AC-5 coverage)
  - [x] T9.7 — Implement T13-T14 KNOWN_ENTITY_TYPES tests (AC-9 coverage)
  - [x] T9.8 — Run `pytest apps/api/tests/test_2fa_schema.py -v` returns 14 passed
  - [x] T9.9 — Run full backend suite `pytest apps/api/tests/ -v --tb=short` returns ≥ 619 passed (605 baseline + 14 new) — **actual: 619/619 passed**

- [x] **T10 — Self-audit + pre-merge verification** (AC: 10, AC-11)
  - [x] T10.1 — Run pre-flight grep checklist (AC-10 7 grep lines) verbatim; all return silent success
  - [x] T10.2 — Run `ruff format --check .` + `ruff check .` from `apps/api/` — both pass
  - [x] T10.3 — Run `infra/scripts/check-all.sh` — 10/10 green
  - [x] T10.4 — `cd apps/web && npm test -- --run` returns unchanged vitest count — **bundled inside check-all.sh, green**
  - [x] T10.5 — `cd apps/web && npx playwright test` returns unchanged Playwright count — **bundled inside check-all.sh (188 visual passed), green**
  - [x] T10.6 — Verify `alembic upgrade head --sql` emission contains `ADD COLUMN totp_secret` AND `CREATE TABLE recovery_codes`
  - [x] T10.7 — Final `git status` shows exactly these modified/new files:
    - **NEW** `apps/api/migrations/versions/0013_users_2fa_columns.py`
    - **NEW** `apps/api/app/core/db/models/_recovery.py`
    - **NEW** `apps/api/tests/test_2fa_schema.py`
    - **MODIFIED** `apps/api/app/core/db/models/__init__.py`
    - **MODIFIED** `apps/api/app/core/db/models/_user.py`
    - **MODIFIED** `apps/api/app/core/config.py`
    - **MODIFIED** `apps/api/app/core/audit.py`
    - **MODIFIED** `apps/api/pyproject.toml`
    - **MODIFIED** `apps/api/uv.lock` (regenerated by T4.2)
    - **MODIFIED** `infra/env.example`
    - **MODIFIED** `infra/docker-compose.yml`
    - **MODIFIED** `apps/api/tests/conftest.py`
    - **MODIFIED** `apps/api/tests/test_audit.py` — *downstream consequence of AC-9: existing `test_known_entity_types_covers_all_call_site_resources` asserts equality with a hardcoded set; added `"recovery_code"` to that set so the test continues to assert "every entry in the registry is documented here" semantics.*

## Dev Notes

### Read-before-modify file inventory

Per the SKILL.md non-negotiable "Read FILES BEING MODIFIED" rule, every UPDATE-class file Story 7.1 touches has been read end-to-end. Current-state snapshots + what-changes / what-must-be-preserved per file:

- **`apps/api/migrations/versions/0012_invite_tokens.py`** (current head). Provides the structural pattern Story 7.1's 0013 migration mirrors: `from __future__ import annotations`, `import sqlalchemy as sa`, `from alembic import op`, `revision = "..."`, `down_revision = "..."`, `branch_labels = None`, `depends_on = None`, then `upgrade()` + `downgrade()`. The 0012 migration uses `op.create_table` + multiple `op.create_index` calls (one UNIQUE for `token_hash`, two non-unique for `generated_at` + `used_by_user_id`); 0013 mirrors this shape but with `op.add_column` calls for the user table plus `op.create_table` for `recovery_codes`. Migration 0009 (`refresh_tokens`) provides the parallel `_helpers.py:UTCDateTime` precedent for how SQLModel-side wrapping interacts with plain-DateTime migrations. **Preserves**: the migration chain (`down_revision = "0012_invite_tokens"`). **Changes**: only the new file 0013 is added — no edit to existing migrations.

- **`apps/api/app/core/db/models/_user.py`** (26 LOC). Current state: 6 fields (`id`, `email`, `display_name`, `role`, `password_hash`, `created_at`, `last_login_at`). **Preserves**: every existing field, field order, the `__tablename__ = "user"` (singular Init 0 convention), the `default_factory=_now_utc` default for `created_at`. **Changes**: adds 2 new optional nullable fields (`totp_secret`, `totp_enabled_at`) between `password_hash` and `created_at`; adds `from sqlalchemy import Column` import; the docstring gains one new sentence about 2FA columns. **Critical preservation**: `seed.py:14`'s `User(email=..., display_name=..., role=..., password_hash=...)` constructor call MUST continue to work — verified via T10 test.

- **`apps/api/app/core/db/models/__init__.py`** (61 LOC). Current state: re-exports every public model symbol; `_invite_models` is imported for side-effect (registers `InviteToken` on `SQLModel.metadata`). **Preserves**: every existing import + every entry in `__all__`. **Changes**: adds `from ._recovery import RecoveryCode` import (alphabetical with `_user`/`_auth` imports) + adds `"RecoveryCode"` to `__all__` (alphabetical between `NoteKind` and `RefreshToken`). The `_invite_models` side-effect import stays as-is — `_recovery` is in the canonical `core/db/models/` directory so it does not need a separate side-effect import path.

- **`apps/api/app/core/config.py`** (116 LOC). Current state: `Settings` class with 11 field groups (App, Volumes, DB, Redis, Auth, Rate-limiting, Observability, Error tracking, Download extensions) + 1 `field_validator` for extensions + 1 `model_validator` for production-secret fail-fast. **Preserves**: every existing field default + the `field_validator` + the existing two `if` blocks in `_block_default_secrets_in_prod`. **Changes**: adds `totp_fernet_key: str = ""` in the `# Auth` block after `admin_password`; extends `_block_default_secrets_in_prod` with a third `if not self.totp_fernet_key` block. NO change to `@lru_cache def get_settings()`.

- **`apps/api/app/core/audit.py`** (45 LOC). Current state: 13-entry `KNOWN_ENTITY_TYPES` frozenset + 1 `record_event(...)` helper that validates `entity_type` membership. **Preserves**: every existing entry + the `record_event` function signature + behavior. **Changes**: adds `"recovery_code"` to the frozenset (alphabetical between `model_print` and `render_selection`) + adds one inline comment line in the docstring's per-entry list.

- **`apps/api/pyproject.toml`** (53 LOC). Current state: 22 deps in `dependencies`, 5 deps in `[project.optional-dependencies]:dev`. **Preserves**: every existing dep. **Changes**: adds `"cryptography>=43",` line in alphabetical position; regenerates `uv.lock`.

- **`apps/api/uv.lock`** (current ~3000 LOC). **Preserves**: the existing lockfile shape; new `cryptography` block added by `uv lock`; transitive deps may shift slightly (e.g., `cffi` pin tightening). NO manual edits to this file — only auto-regenerated.

- **`infra/env.example`** (current ~50 LOC, post-Stories 6.6 + 6.7). **Preserves**: every existing line. **Changes**: adds `# TOTP_FERNET_KEY — generate via: python -c ...` comment + `TOTP_FERNET_KEY=` active line, both placed immediately after `JWT_SECRET=...`.

- **`infra/docker-compose.yml`** (147 LOC). **Preserves**: every existing service + every existing env-var. **Changes**: adds exactly one line `TOTP_FERNET_KEY: ${TOTP_FERNET_KEY}` to `services.api.environment` block, immediately after `JWT_SECRET: ${JWT_SECRET}`. NO change to `services.arq-worker` or other service blocks.

- **`apps/api/tests/conftest.py`** (65 LOC). Current state: 3 fixtures (`_patch_arq_pool` autouse, `_isolated_db` autouse session-scope, `client` per-test). **Preserves**: every existing fixture + every existing env-var assignment. **Changes**: adds one new `os.environ["TOTP_FERNET_KEY"] = "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="` line in `_isolated_db`, between `JWT_SECRET` and `PORTAL_CONTENT_DIR`.

### Architecture decisions realized

- **Decision D (architecture.md §1495-1513)** — `users.totp_secret VARCHAR(255) NULL` + `users.totp_enabled_at DATETIME NULL` + `TOTP_FERNET_KEY: str` Settings field. All three surfaces shipped in this story.
- **Decision E (architecture.md §1515-1533)** — `recovery_codes` table with 7 columns (`id`, `user_id`, `code_hash`, `batch_id`, `generated_at`, `used_at`, `invalidated_at`) + 2 non-unique indexes + bcrypt-at-rest discipline (the `code_hash VARCHAR(60)` length pin reserves the bcrypt-2b output shape). The audit-trail per-row capability (`invalidated_at` lifecycle) is shipped in the schema; the regenerate/disable transitions land in Story 7.5.

### Architecture decisions deferred to Epic 7 later stories

- **Decision F (architecture.md §1536-1557)** — `enforce_2fa_for_roles: list[UserRole]` config flag + fail-fast for `UserRole.agent`. Lands in Story 7.4. NOT in Story 7.1 scope — the agent-role fail-fast applies to the enforcement check, which doesn't exist until 7.4.
- **`pyotp` dependency.** Story 7.2 adds `pyotp>=2.9` + the TOTP secret generation + 6-digit verification logic. NOT in Story 7.1 — premature.
- **`apps/api/app/modules/auth/totp/` module directory.** Stories 7.2/7.3/7.5 create `service.py`, `router.py`, `regenerate_router.py`. NOT in Story 7.1 scope — Story 7.1 only ships schema + Settings + KNOWN_ENTITY_TYPES.

### Previous story intelligence (Story 6.7)

Story 6.7 (per-member share-token cap, shipped commits `12ba359` + codex fix-up `54af50a`, Sesja Y close-out). Key inheritances and lessons:

- **Compose env wiring forgotten in dev commit, caught by Codex review on fix-up commit.** Story 7.1 elevates this from a Codex-catch-and-fix to a mandatory pre-merge AC (AC-6 + AC-10 grep checklist) so the same defect cannot ship. Team Agreement A4 (Epic 6 retro) is now encoded structurally in Story 7.1.
- **uv.lock staleness was the Story 6.4 defect class.** Story 7.1 includes `uv lock` regen as a mandatory T4 task with verification grep — same elevation to AC level.
- **`_helpers.py:UTCDateTime` + `uuid_fk()` pattern.** Reused verbatim in `_recovery.py` per AC-2. No new helper functions needed.
- **`_invite_models` side-effect import in `__init__.py`.** Story 7.1's `_recovery.py` lives in the canonical `core/db/models/` directory, so the standard `from ._recovery import RecoveryCode` line in `__init__.py` is sufficient — no side-effect import duplication needed.
- **Story 6.7 Dev Agent Record back-fill is OPTIONAL per Epic 6 retro Action Item 3.** Story 7.1 dev agent does NOT need to back-fill 6.7 — that's a separate opportunistic task.

### Pattern reuses from Epic 6 (high-leverage precedents)

1. **Mirror Init 0 precedent for new tables.** `recovery_codes` is shaped after `invite_tokens` (UUID PK, `user.id` FK, plain `sa.DateTime` at migration layer with `UTCDateTime` wrapper at SQLModel layer). Saved significant design time.
2. **Verbatim test-name checklist (AC-7).** 14 named test cases ensure the dev agent's TDD red phase has no ambiguity. Started failing → green when all 14 pass + 605 baseline holds.
3. **`feat → codex fix-up` commit convention.** Story 7.1 ships as one `feat(api): Story 7.1 …` commit. Any post-Codex review findings ship as separate `fix(api): Story 7.1 codex fix-up — <subject>` commits.
4. **Pre-flight grep discipline (AC-10).** Encoded as a 7-line checklist the dev agent runs before commit.

### Doc-drift items resolved/cited (from Epic 6 retro catalog)

- **Item 1 (alembic-vs-migrations path).** Story 7.1 spec uses the live `apps/api/migrations/versions/` path verbatim. Note: epics.md:1662 still says "alembic/versions/" — that planning-text correction is deferred to `bmad-correct-course`.
- **Item 2 (KNOWN_ENTITY_TYPES is entity-type registry, NOT action registry).** AC-9 encodes this clarification: 5 E7 action names are free-form strings (NOT registered); only the new `recovery_code` entity_type is added to the frozenset. The audit emissions for `auth.totp.enrolled` etc. use existing `user` entity_type per the precedent.
- **Item 4 (`Role` vs `UserRole`).** Story 7.1 imports `UserRole` (correct enum name); never references `Role`.
- **Items 6, 12, 13, 14 (Decision G + share path drift).** N/A for Story 7.1 (no middleware / no share router touched).

### Doc-drift items deferred to `bmad-correct-course` (PRE-Story 7.2)

Per Epic 6 retro Action Items §1 and the user's explicit note in sprint-status (Sesja Z): `bmad-correct-course` should run BEFORE Story 7.2 spec creation, because Stories 7.2/7.4 carry the bulk of the 4 wrong-assumption surfaces (frontend routing path, `core/auth/middleware.py` non-existence, Decision G middleware ordering wording, `Role` shorthand). Story 7.1 itself does NOT touch any of those surfaces, so it can ship without the correct-course pass landing first. The 4 deferred drift items remain logged for the next session.

### What Codex will catch that pytest won't (pre-flagged per Epic 6 retro discovery)

- **uv.lock not regenerated** (Story 6.4 lesson). Mitigated: AC-4 + T4.4 + AC-10 grep.
- **Compose env not propagated** (Stories 6.6 + 6.7 lesson). Mitigated: AC-6 + T6.2 + AC-10 grep.
- **Migration column-shape vs SQLModel field-type mismatch** (NEW risk class). Catches: SQLModel says `str | None` but migration says `VARCHAR NOT NULL`. Mitigated: T9.3 + T1.3 explicit assertion on column nullability.
- **Fernet key length wrong** (NEW risk). Story 7.1 only validates truthiness; if the deterministic test key is malformed, Story 7.2 will discover it. Mitigated: deterministic 44-char base64 value in AC-8.

### Project Structure Notes

- **Alignment with unified project structure.** All new files land in canonical Init 0 directories:
  - `apps/api/migrations/versions/0013_*.py` (Alembic-managed; consistent with 0001-0012)
  - `apps/api/app/core/db/models/_recovery.py` (parallel to `_auth.py`, `_user.py`, `_audit.py`, `_entities.py`)
  - `apps/api/tests/test_2fa_schema.py` (canonical test-file naming: `test_<area>.py`)

- **Detected conflicts or variances.** None structural. Two doc-drift items resolved at code-creation time:
  1. Migration path (`apps/api/migrations/versions/` not `apps/api/alembic/versions/`).
  2. KNOWN_ENTITY_TYPES is entity-type registry (only `recovery_code` added; the 5 action-name strings live in `record_event(action="...")` calls in 7.2/7.3/7.5).

- **Deferred-quick-dev preconditions surfaced by Epic 6 retro (NOT blockers for Story 7.1; tracked for future).**
  - Epic 6 retro Action Items §5 + §6: add `check-all.sh` stages diffing Settings ↔ env.example ↔ docker-compose.yml AND `uv lock --check`. Recommended by retro to ship BEFORE Story 7.1. As of Sesja Z (2026-05-19) these stages have NOT shipped. Story 7.1 manually encodes the same checks via AC-6 + AC-10 grep checklist. The check-all.sh stages remain a separate `chore(infra)` commit pending.
  - Epic 6 retro Action Item §4: promote per-file `client` fixture to `apps/api/tests/conftest.py`. Threshold reached (4 files: 6.3 invite_admin, 6.4 invite_register, 6.5 share_member_permission, 6.7 ratelimit_share_cap). Story 7.1 does NOT author a new per-file `client` fixture (no new endpoints), so this promotion is NOT bundled here — recommended as a separate `chore(api)` commit pre-Story-7.2.
  - Epic 6 retro Critical Path §3: `bmad-correct-course` for 17 doc-drift items. Story 7.1 spec acknowledges 4 items relevant to its scope (items 1, 2, 4, 12) and encodes correct behavior. The remaining 13 items are non-blocking for Story 7.1; should land in correct-course BEFORE Story 7.2.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.1 — Alembic migration `0013_users_2fa_columns` + recovery-codes table + Fernet key plumbing] — story foundation, dependencies, FR/anchor binding.
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision D — 2FA column shape on `users` table (Fernet-encrypted `totp_secret` + nullable `totp_enabled_at`)] — column shape + Fernet boundary.
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision E — Recovery codes schema (bcrypt-at-rest, batch grouping, lifecycle columns)] — recovery_codes table + bcrypt cost + batch lifecycle.
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-2FA-1] — enrollment + recovery code mandatory generation.
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-AUDIT-1] — 16 new audit-log actions + entity_type registry semantics.
- [Source: _bmad-output/planning-artifacts/prd.md#NFR5-INT-1] — agent-account null-op migration property.
- [Source: _bmad-output/implementation-artifacts/epic-6-retro-2026-05-19.md#Action items — Epic 6 retrospective] — drift catalog, lesson elevation rationale, deferred preconditions.
- [Source: apps/api/migrations/versions/0012_invite_tokens.py] — Alembic precedent shape mirrored by 0013.
- [Source: apps/api/app/core/db/models/_auth.py] — `RefreshToken` precedent for `UTCDateTime` wrapper + `uuid_fk` helper usage.
- [Source: apps/api/app/core/db/models/_user.py] — current `User` model; baseline for 2-field extension.
- [Source: apps/api/app/core/config.py] — current Settings shape + `_block_default_secrets_in_prod` validator precedent.
- [Source: apps/api/app/core/audit.py] — current `KNOWN_ENTITY_TYPES` frozenset + `record_event()` validation.
- [Source: apps/api/pyproject.toml] — current dep list; insertion point for `cryptography>=43`.
- [Source: apps/api/tests/conftest.py] — `_isolated_db` autouse fixture pattern for test env-var override.
- [Source: infra/env.example] — pattern for documenting required env-vars + generation hints.
- [Source: infra/docker-compose.yml] — `services.api.environment` block for forwarding env-vars to the container.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — claude-opus-4-7[1m], session 2026-05-19.

### Debug Log References

Three transient TDD-red bumps surfaced and were fixed in-session:

1. **`test_migration_0013_creates_recovery_codes_indexes` — `unique is False` vs `unique == 0`.** SQLAlchemy's `inspect(engine).get_indexes(...)` on SQLite returns `unique` as **int 0** (not bool False); the strict-identity check `is False` failed even though the index is non-unique. Fixed by switching to `not idx[...]["unique"]` (truthy-style) which is correct for both `0` and `False`.
2. **`test_recovery_code_create_round_trip_via_init_schema` — FK ordering on single-flush.** SQLite enforces FK per-statement (not deferred to COMMIT), and SQLAlchemy's UoW topological sort does **not** reliably order `User` before `RecoveryCode` when the FK is declared via `Field(sa_column=uuid_fk(...))` rather than an SQLAlchemy `relationship()`. Fixed by splitting the insert into two `with Session(...)` blocks (commit User, then commit RecoveryCode) — same pattern existing test_invite_models tests use.
3. **`test_known_entity_types_includes_recovery_code` — FK on `audit_log.actor_user_id`.** Even with `ondelete="SET NULL"` and `nullable=True`, the FK to `user.id` is enforced on INSERT — passing a random UUID actor_id without a parent user row raised `IntegrityError`. Fixed by inserting a real `User` row for the actor first, then calling `record_event(...)`.

Additionally, pre-existing `test_audit.py::test_known_entity_types_covers_all_call_site_resources` flipped red because it asserts equality with a hardcoded set; updated the expected set to include `"recovery_code"`. This is a legitimate downstream update — the test's semantic is "every registered entity_type is documented in this list", and Story 7.1 adds one entry. Documented in T10.7.

Ruff reformatted `apps/api/app/core/config.py` once on first `ruff format` pass (escaped `"` quotes inside the new validator's error message reflowed to use embedded `'...'` quotes) — diff is whitespace/quote-style only, no semantic change.

Ruff RUF002 flagged the `×` (multiplication sign) in `apps/api/app/core/db/models/_recovery.py` docstring; replaced with the literal word `times`.

### Completion Notes List

- **Schema + plumbing only.** No endpoints, no router, no frontend, no `pyotp`, no `auth/totp/service.py` — all consciously deferred to Stories 7.2 / 7.3 / 7.5 / 7.4 per the spec scope.
- **Migration 0013** chains `0012_invite_tokens` → `0013_users_2fa_columns`. `upgrade()` adds two nullable `user` columns + creates `recovery_codes` with 7 columns + 2 non-unique indexes (`ix_recovery_codes_user_id`, `ix_recovery_codes_batch_id`). `downgrade()` reverses in strict LIFO. Verified by tests T1-T6 of AC-7.
- **`RecoveryCode` SQLModel** uses the `_helpers.py:UTCDateTime` + `_helpers.py:uuid_fk` precedent from `RefreshToken`; CASCADE on `user_id` FK matches the AC-1 binding bullet.
- **`User.totp_secret` + `User.totp_enabled_at`** both `Optional` with `default=None`; `seed_admin` constructor signature unchanged (verified by `test_seed_admin_unchanged_after_2fa_columns`).
- **`cryptography>=43`** added to `pyproject.toml`; `uv lock` regen pulled cryptography 48.0.0 + cffi 2.0.0 + pycparser 3.0 transitive; `uv lock --check` exits 0; `docker compose build api` succeeds on `python:3.12-slim`.
- **`TOTP_FERNET_KEY: str = ""`** added to `Settings` in the `# Auth` block after `admin_password`; `_block_default_secrets_in_prod` validator extended with a third `if not self.totp_fernet_key` block that includes the literal `python -c "from cryptography.fernet import Fernet; ..."` generation hint in the error message.
- **`infra/env.example`** gained an active `TOTP_FERNET_KEY=` line with preceding generation-hint comment, immediately after `JWT_SECRET=`. **`infra/docker-compose.yml`** `services.api.environment` forwards `TOTP_FERNET_KEY: ${TOTP_FERNET_KEY}` (NO default — operator MUST supply). `arq-worker` env block intentionally left unchanged (no auth surface there).
- **conftest deterministic test key** `ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=` set on session-scope `_isolated_db` between `JWT_SECRET` and `PORTAL_CONTENT_DIR`. Verified the key parses through `cryptography.fernet.Fernet(...)` constructor (32 url-safe-base64 bytes).
- **`KNOWN_ENTITY_TYPES`** grew from 13 → 14 with `"recovery_code"` added in alphabetical position between `model_print` and `render_selection`; docstring comment block updated to match.
- **14 new tests** in `apps/api/tests/test_2fa_schema.py` all green (T1-T14 per the AC-7 binding table).
- **Pre-flight grep checklist (AC-10)** ran clean — all 7 lines returned silent success.
- **Full backend suite: 619/619 passed** (605 baseline + 14 new). Final `infra/scripts/check-all.sh` returns **10/10 green** (ruff format + check both api + workers/render; web typecheck + lint + vitest; pytest api + workers/render; web visual regression 188 specs).
- **Decision F deferred to Story 7.4** as planned. No `enforce_2fa_for_roles` config flag in this story.
- **Decision D + E foundation shipped.** Story 7.2 can now build `auth/totp/service.py` (TOTP secret generation + Fernet encrypt) and Story 7.3 can build the partial-auth login flow against the schema this story laid down.
- **No Codex fix-up surfaces remain unaddressed pre-merge.** The Stories 6.4 + 6.6 + 6.7 lesson (uv.lock staleness, compose env wiring) was elevated to mandatory pre-merge ACs (AC-4 + AC-6 + AC-10 grep checklist) and all checks pass on the dev commit.

### File List

**NEW**
- `apps/api/migrations/versions/0013_users_2fa_columns.py`
- `apps/api/app/core/db/models/_recovery.py`
- `apps/api/tests/test_2fa_schema.py`

**MODIFIED**
- `apps/api/app/core/db/models/__init__.py`
- `apps/api/app/core/db/models/_user.py`
- `apps/api/app/core/config.py`
- `apps/api/app/core/audit.py`
- `apps/api/pyproject.toml`
- `apps/api/uv.lock`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_audit.py` (downstream of AC-9 — added `"recovery_code"` to the hardcoded expected-set assertion)
- `infra/env.example`
- `infra/docker-compose.yml`

## Change Log

- 2026-05-19 — Story 7.1 implementation complete (Sesja AB, bmad-dev-story).
  - Alembic 0013 chained from 0012, adds `user.totp_secret` + `user.totp_enabled_at` (both nullable) + creates `recovery_codes` (7 columns, 2 non-unique indexes) per Decisions D + E.
  - `RecoveryCode` SQLModel + `RecoveryCode` re-export from `app.core.db.models`.
  - `User` SQLModel extended with 2 nullable fields (`totp_secret`, `totp_enabled_at`); `seed_admin` constructor compatibility preserved.
  - `cryptography>=43` added to `pyproject.toml`; `uv lock` regenerated (resolves to cryptography 48.0.0).
  - `TOTP_FERNET_KEY: str` added to `Settings`; production fail-fast validator extended.
  - `infra/env.example` + `infra/docker-compose.yml` forward the new env-var to the `api` container.
  - `apps/api/tests/conftest.py` provides a session-scope deterministic test key.
  - `"recovery_code"` added to `KNOWN_ENTITY_TYPES` frozenset (registry now has 14 entries).
  - `apps/api/tests/test_2fa_schema.py` adds 14 named tests covering migration + model + Settings + KNOWN_ENTITY_TYPES; full backend suite passes 619/619.
  - `apps/api/tests/test_audit.py` expected-set assertion updated to include `"recovery_code"` (downstream of AC-9).
