"""Story 7.1 — schema + plumbing tests for 2FA columns + recovery_codes table.

Covers AC-1 (migration 0013), AC-2 (RecoveryCode SQLModel), AC-3 (User SQLModel
extension), AC-5 (TOTP_FERNET_KEY Settings + production fail-fast), and AC-9
(KNOWN_ENTITY_TYPES). 14 named test cases — names are binding per the story
spec's AC-7 table.

Migration tests use the same per-test DB rig as ``test_migration_0012.py``:
``env.py`` reads ``get_settings().database_url`` and ignores the URL passed via
Alembic ``Config``, so DATABASE_URL must be overridden via env var for the
duration of each migration test.
"""

from __future__ import annotations

import datetime
import os
import sqlite3
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.audit import KNOWN_ENTITY_TYPES, record_event
from app.core.config import get_settings
from app.core.db.models import RecoveryCode, User, UserRole
from app.core.db.seed import seed_admin
from app.core.db.session import create_engine_for_url, get_engine, init_schema


def _alembic_cfg(db_path: Path) -> Config:
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


@pytest.fixture
def _fresh_migration_db(tmp_path: Path) -> Iterator[Path]:
    """Per-test isolated SQLite + DATABASE_URL override so env.py picks it up."""
    db_path = tmp_path / "migration.db"
    prior_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        yield db_path
    finally:
        if prior_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prior_url
        get_settings.cache_clear()
        get_engine.cache_clear()


# ---------------------------------------------------------------------------
# AC-1 — migration 0013 upgrade / downgrade semantics (T1..T6)
# ---------------------------------------------------------------------------


def test_migration_0013_advances_head(_fresh_migration_db: Path) -> None:
    db_path = _fresh_migration_db
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "0013_users_2fa_columns")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    assert rows == [("0013_users_2fa_columns",)]


def test_migration_0013_creates_recovery_codes_table(_fresh_migration_db: Path) -> None:
    db_path = _fresh_migration_db
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "0013_users_2fa_columns")
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    assert "recovery_codes" in inspector.get_table_names()
    cols = {c["name"] for c in inspector.get_columns("recovery_codes")}
    assert cols == {
        "id",
        "user_id",
        "code_hash",
        "batch_id",
        "generated_at",
        "used_at",
        "invalidated_at",
    }
    fks = inspector.get_foreign_keys("recovery_codes")
    assert len(fks) == 1
    fk = fks[0]
    assert fk["referred_table"] == "user"
    assert fk["referred_columns"] == ["id"]
    assert fk["constrained_columns"] == ["user_id"]
    assert fk.get("options", {}).get("ondelete", "").upper() == "CASCADE"


def test_migration_0013_adds_user_totp_columns(_fresh_migration_db: Path) -> None:
    db_path = _fresh_migration_db
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "0013_users_2fa_columns")
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    cols_by_name = {c["name"]: c for c in inspector.get_columns("user")}
    assert "totp_secret" in cols_by_name
    assert "totp_enabled_at" in cols_by_name
    totp_secret = cols_by_name["totp_secret"]
    assert totp_secret["nullable"] is True
    # SQLAlchemy reports the dialect-specific type. On SQLite, String(255)
    # appears as VARCHAR(255). Compare via the string representation.
    assert "VARCHAR" in str(totp_secret["type"]).upper()
    assert "255" in str(totp_secret["type"])
    totp_enabled_at = cols_by_name["totp_enabled_at"]
    assert totp_enabled_at["nullable"] is True
    assert "DATETIME" in str(totp_enabled_at["type"]).upper()


def test_migration_0013_creates_recovery_codes_indexes(_fresh_migration_db: Path) -> None:
    db_path = _fresh_migration_db
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "0013_users_2fa_columns")
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    idx_by_name = {ix["name"]: ix for ix in inspector.get_indexes("recovery_codes")}
    assert "ix_recovery_codes_user_id" in idx_by_name
    assert idx_by_name["ix_recovery_codes_user_id"]["column_names"] == ["user_id"]
    assert not idx_by_name["ix_recovery_codes_user_id"]["unique"]
    assert "ix_recovery_codes_batch_id" in idx_by_name
    assert idx_by_name["ix_recovery_codes_batch_id"]["column_names"] == ["batch_id"]
    assert not idx_by_name["ix_recovery_codes_batch_id"]["unique"]
    # NO UNIQUE indexes anywhere on the table (AC-1 binding bullet).
    assert all(not ix["unique"] for ix in idx_by_name.values())


def test_migration_0013_preserves_existing_user_rows_null_default(
    _fresh_migration_db: Path,
) -> None:
    db_path = _fresh_migration_db
    cfg = _alembic_cfg(db_path)
    # Step 1: upgrade only to 0012 so the user table exists WITHOUT totp_* cols.
    command.upgrade(cfg, "0012_invite_tokens")
    # Step 2: insert admin + agent + member rows via raw SQL.
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat(sep=" ")
    rows = [
        (str(uuid.uuid4()), "admin@x", "Admin", UserRole.admin.value, "h1", now, None),
        (str(uuid.uuid4()), "agent@x", "Agent", UserRole.agent.value, "h2", now, None),
        (str(uuid.uuid4()), "member@x", "Member", UserRole.member.value, "h3", now, None),
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            'INSERT INTO "user" (id, email, display_name, role, password_hash, created_at, '
            "last_login_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    # Step 3: upgrade to head (0013) — ADD COLUMN should leave existing rows NULL.
    command.upgrade(cfg, "0013_users_2fa_columns")
    with sqlite3.connect(db_path) as conn:
        result = conn.execute(
            'SELECT email, totp_secret, totp_enabled_at FROM "user" ORDER BY email'
        ).fetchall()
    assert result == [
        ("admin@x", None, None),
        ("agent@x", None, None),
        ("member@x", None, None),
    ]


def test_migration_0013_downgrade_reverses_clean(_fresh_migration_db: Path) -> None:
    db_path = _fresh_migration_db
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "0013_users_2fa_columns")
    command.downgrade(cfg, "-1")
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    assert "recovery_codes" not in inspector.get_table_names()
    user_cols = {c["name"] for c in inspector.get_columns("user")}
    assert "totp_secret" not in user_cols
    assert "totp_enabled_at" not in user_cols
    # alembic_version stamp rolls back to 0012.
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    assert rows == [("0012_invite_tokens",)]


# ---------------------------------------------------------------------------
# AC-2 — RecoveryCode SQLModel registration + round-trip (T7..T8)
# ---------------------------------------------------------------------------


def test_recovery_code_model_registered_on_metadata() -> None:
    from sqlmodel import SQLModel

    assert RecoveryCode.__tablename__ == "recovery_codes"
    assert "recovery_codes" in SQLModel.metadata.tables
    instance = RecoveryCode(
        user_id=uuid.uuid4(),
        code_hash="$2b$12$" + "x" * 53,
        batch_id=uuid.uuid4(),
    )
    assert isinstance(instance.id, uuid.UUID)
    assert isinstance(instance.generated_at, datetime.datetime)
    # Defaults populate cleanly even though we did not pass them.
    assert instance.used_at is None
    assert instance.invalidated_at is None


def test_recovery_code_create_round_trip_via_init_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "init_schema.db"
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    init_schema(engine)
    # First a parent user row (FK to user.id is NOT NULL).
    user_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    code_hash = "$2b$12$" + "y" * 53
    # Two commits — SQLite enforces FK per-statement, and SQLAlchemy's
    # FK-via-sa_column path does not always topologically order multi-table
    # inserts in one flush.
    with Session(engine) as session:
        session.add(
            User(
                id=user_id,
                email="rc-roundtrip@x",
                display_name="RC",
                role=UserRole.member,
                password_hash="h",
            )
        )
        session.commit()
    with Session(engine) as session:
        session.add(
            RecoveryCode(
                user_id=user_id,
                code_hash=code_hash,
                batch_id=batch_id,
            )
        )
        session.commit()
    with Session(engine) as session:
        fetched = session.exec(select(RecoveryCode).where(RecoveryCode.user_id == user_id)).one()
    assert fetched.user_id == user_id
    assert fetched.batch_id == batch_id
    assert fetched.code_hash == code_hash
    assert fetched.used_at is None
    assert fetched.invalidated_at is None
    assert fetched.generated_at.tzinfo is not None  # UTCDateTime wrapper rehydrates UTC.


# ---------------------------------------------------------------------------
# AC-3 — User SQLModel schema match + seed_admin compat (T9..T10)
# ---------------------------------------------------------------------------


def test_user_model_matches_migration_0013_schema(_fresh_migration_db: Path) -> None:
    db_path = _fresh_migration_db
    cfg = _alembic_cfg(db_path)
    # Upgrade to head (not just 0013) so the User SQLModel's columns added
    # by later migrations (Story 8.1's is_active + last_active_at on 0014)
    # match the DB schema. The test's binding intent — verifying the totp
    # columns from 0013 round-trip cleanly through the model — stays intact.
    command.upgrade(cfg, "head")
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    user_id = uuid.uuid4()
    enabled_at = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    with Session(engine) as session:
        session.add(
            User(
                id=user_id,
                email="schema-match@x",
                display_name="SchemaMatch",
                role=UserRole.member,
                password_hash="h",
                totp_secret="ciphertext-placeholder",
                totp_enabled_at=enabled_at,
            )
        )
        session.commit()
    with Session(engine) as session:
        fetched = session.exec(select(User).where(User.id == user_id)).one()
    assert fetched.totp_secret == "ciphertext-placeholder"
    assert fetched.totp_enabled_at is not None
    assert fetched.totp_enabled_at.tzinfo is not None
    assert fetched.totp_enabled_at == enabled_at


def test_seed_admin_unchanged_after_2fa_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "seed.db"
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    init_schema(engine)
    seed_admin(engine, email="admin@local", password="x", display_name="Admin")
    with Session(engine) as session:
        row = session.exec(select(User).where(User.email == "admin@local")).one()
    assert row.role == UserRole.admin
    assert row.totp_secret is None
    assert row.totp_enabled_at is None


# ---------------------------------------------------------------------------
# AC-5 — TOTP_FERNET_KEY production fail-fast + dev-empty-OK (T11..T12)
# ---------------------------------------------------------------------------


def test_totp_fernet_key_missing_in_production_warns_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story 7.1 production-incident relax (2026-05-19).

    Original Story 7.1 fail-fast on missing key in production blocked deploy
    on `.190` (no key in infra/.env, no encryption ops run yet — schema-only
    story). Relaxed to warning; the actual fail-fast belongs in Story 7.2
    where the key is first consumed by enrollment endpoint.
    """
    import warnings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "real-jwt-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "real-admin-password")
    monkeypatch.delenv("BCRYPT_ROUNDS", raising=False)
    monkeypatch.delenv("TOTP_FERNET_KEY", raising=False)
    get_settings.cache_clear()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            settings = get_settings()
            assert settings.totp_fernet_key == ""
            messages = [str(w.message) for w in caught]
            assert any("TOTP_FERNET_KEY is unset" in m for m in messages), (
                f"expected production-without-key warning, got: {messages}"
            )
    finally:
        get_settings.cache_clear()


def test_totp_fernet_key_empty_ok_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.delenv("TOTP_FERNET_KEY", raising=False)
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.environment == "dev"
        assert settings.totp_fernet_key == ""
    finally:
        get_settings.cache_clear()


def test_bcrypt_rounds_below_12_rejected_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "real-jwt-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "real-admin-password")
    monkeypatch.setenv("BCRYPT_ROUNDS", "4")
    monkeypatch.delenv("TOTP_FERNET_KEY", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(ValidationError) as excinfo:
            get_settings()
        assert "bcrypt_rounds must be >= 12 in production" in str(excinfo.value)
    finally:
        get_settings.cache_clear()


def test_totp_fernet_key_invalid_shape_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix-up for Story 7.1 Codex P2 — malformed Fernet key must fail at
    Settings instantiation, not deferred to first enroll-confirm use."""
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("TOTP_FERNET_KEY", "not-a-fernet-key")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValidationError) as excinfo:
            get_settings()
        message = str(excinfo.value)
        assert "TOTP_FERNET_KEY must be a valid Fernet key" in message
    finally:
        get_settings.cache_clear()


def test_totp_fernet_key_generated_key_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Companion to the invalid-shape test — a freshly generated Fernet key
    must instantiate Settings cleanly."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("TOTP_FERNET_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.totp_fernet_key  # non-empty
        # Round-trip: the stored value must reconstruct a working Fernet.
        Fernet(settings.totp_fernet_key.encode())
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# AC-9 — KNOWN_ENTITY_TYPES + record_event recovery_code roundtrip (T13..T14)
# ---------------------------------------------------------------------------


def test_known_entity_types_includes_recovery_code() -> None:
    assert "recovery_code" in KNOWN_ENTITY_TYPES
    # The session-scoped _isolated_db fixture already ran init_schema, so the
    # session engine has both the audit_log table and the recovery_codes table.
    # audit_log.actor_user_id has FK to user.id, so insert a real user first.
    actor_id = uuid.uuid4()
    code_id = uuid.uuid4()
    with Session(get_engine()) as session:
        session.add(
            User(
                id=actor_id,
                email=f"audit-actor-{actor_id}@x",
                display_name="AuditActor",
                role=UserRole.member,
                password_hash="h",
            )
        )
        session.commit()
    record_event(
        get_engine(),
        action="auth.recovery_code.used",
        entity_type="recovery_code",
        entity_id=code_id,
        actor_user_id=actor_id,
    )
    # Read back the audit row we just wrote.
    from app.core.db.models import AuditLog

    with Session(get_engine()) as session:
        row = session.exec(
            select(AuditLog)
            .where(AuditLog.entity_type == "recovery_code")
            .where(AuditLog.entity_id == code_id)
        ).one()
    assert row.action == "auth.recovery_code.used"
    assert row.actor_user_id == actor_id


def test_known_entity_types_count_includes_one_new_addition() -> None:
    # Story 6.1 brought the count to 13 (added invite_token); Story 7.1 adds
    # recovery_code bringing it to 14; Story 33.2 adds slicer_profile for admin
    # profile-import audit, bringing it to 15; Story 42.4 adds tag_group for the
    # admin tag-group governance audit, bringing it to 16; Story 47.5 retires
    # the legacy taxonomy entity type, bringing it to 15. Guard against drift.
    assert len(KNOWN_ENTITY_TYPES) == 15
